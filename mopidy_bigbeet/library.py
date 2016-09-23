from __future__ import unicode_literals

import datetime
import logging
import os
import sys

from mopidy_bigbeet.schema import schema
from mopidy import backend
from mopidy.exceptions import ExtensionError
from mopidy.models import Album, Artist, Ref, SearchResult, Track

from uritools import uricompose, uriencode, urisplit

logger = logging.getLogger(__name__)

# TODO:
# - Grouping if result set greater than x
# - search genre include children genres
# - show Compilations and Singletons below Genre (Volksmusik)
# - use query[<filter>] = <filter_value> instead of query['filter^']


class BigbeetLibraryProvider(backend.LibraryProvider):
    ROOT_URI = 'bigbeet:root'
    root_directory = Ref.directory(uri=ROOT_URI, name='Local (bigbeet)')
    FIRST_LEVEL = [
        'Genre',
        'Grouping',
        'Hoerspiele',
        'Singletons',
        'Compilations',
        'Label',
        'Format',
        'Samplerate',
        'Year',
        # 'Added At',
    ]


    def __init__(self, *args, **kwargs):
        super(BigbeetLibraryProvider, self).__init__(*args, **kwargs)
        # schema.connect_db(self.backend.db_path)
        try:
            schema._initialize(self.backend.config)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            import pdb; pdb.set_trace()
            pass

    def search(self, query=None, uris=None, exact=False):
        logger.debug(u'Search query: %s in uris: %s', query, uris)
        query = self._sanitize_query(query)
        logger.debug(u'Search sanitized query: %s ' % query)
        albums = []
        if not query:
            uri = 'bigbeet:search-all'
            tracks = schema.Track.select()
            albums = schema.Album.select()
        else:
            uri = uricompose('bigbeet',
                             None,
                             'search',
                             query)
            schemas, bb_query = self._build_query_expressions(query, exact)
            joined_schema = self._build_joins(schemas, u'track')
            tracks = joined_schema.where(*bb_query)
            if 'track_name' not in query:
                # when trackname queried dont search for albums
                joined_schema = self._build_joins(schemas, u'album')
                albums = joined_schema.where(*bb_query)
        logger.debug(u"Query found %s tracks and %s albums"
                     % (len(tracks), len(albums)))
        return SearchResult(
            uri=uri,
            tracks=[self._convert_track(track) for track in tracks],
            albums=[self._convert_album(album) for album in albums]
        )

    def _browse_root(self):
        for level in self.FIRST_LEVEL:
            yield Ref.directory(
                uri=uricompose('bigbeet',
                               None,
                               level.lower(),
                               None),
                name=level)

    def _browse_genre(self, query=None):
        if query:
            genre = schema.Genre.get(schema.Genre.id == int(query['genre'][0]))
            subgenres = schema.Genre.select().where(
                schema.Genre.parent == genre.id)
            if subgenres:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(filter='all_artists',
                                        all_artists=genre.id,
                                        genre=genre.id)),
                    name="All Artists"
                )
            for subgenre in subgenres:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'genre',
                                   dict(genre=subgenre.id)),
                    name="- {}".format(subgenre.name)
                )
            for artist in genre.artists:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'albums',
                                   dict(artist=artist.id,
                                        filter=u'artist',
                                        filter_value=artist.id)),
                    name=artist.name
                    )
        else:
            for genre in schema.Genre.select().where(schema.Genre.parent == None).order_by(schema.Genre.name):
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'genre',
                                   dict(genre=genre.id)),
                    name=genre.name if bool(genre.name) else u'No Genre')

    def _browse_groupings(self, query):
        groupings = schema.Track.select(schema.Track.grouping).distinct().order_by(schema.Track.grouping)
        for g in groupings:
            yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(grouping=g.grouping, filter=u'grouping')),
                    name=g.grouping)


    def _browse_artists(self, query):
        if query['filter'][0] == u'label':
            artists = schema.Artist.select().join(schema.Album).where(schema.Album.label_id == query['label'][0]).distinct()
        elif query['filter'][0] == u'grouping':
            artists = schema.Artist.select().join(schema.Album).join(schema.Track).where(schema.Track.grouping == query['grouping'][0]).distinct()
        elif query['filter'][0] == u'samplerate':
            artists = schema.Artist.select().join(schema.Album).join(schema.Track).where(schema.Track.samplerate == query['samplerate'][0]).distinct()
        elif query['filter'][0] == u'format':
            artists = schema.Artist.select().join(schema.Album).join(schema.Track).where(schema.Track.format == query['format'][0]).distinct()
        elif query['filter'][0] == u'added_at':
            artists = schema.Artist.select().join(schema.Album).join(schema.Track).where(schema.Track.added == query['added_at'][0]).distinct()
        elif query['filter'][0] == u'year':
            artists = schema.Artist.select().join(schema.Album).where(schema.Album.original_year == query['year'][0]).distinct()
        elif query['filter'][0] == u'all_artists':
            genre = schema.Genre.get(id=query['genre'][0])
            # import pdb; pdb.set_trace()
            genres = schema._find_children(genre,[genre])
            logger.info([g.name for g in genres])
            artists = []
            for genre in genres:
                artists += [a for a in schema.Artist.select().where(schema.Artist.genre_id == genre.id)]
        elif query['filter'][0] == u'genre':
            artists = schema.Artist.select().where(schema.Artist.genre_id == query['genre'][0])
        else:
            artists = schema.Artist.select()
        for artist in sorted(artists, key=lambda x: x.name):
            yield Ref.directory(
                uri=uricompose('bigbeet',
                                None,
                                'albums',
                                dict(artist=artist.id,
                                     filter=query['filter'][0],
                                     filter_value=query[query['filter'][0]][0]
                                     )),
                    name=artist.name
                    )


    def _browse_albums(self, query):
        if query['filter'][0] == u'label':
            albums = schema.Album.select().where(schema.Album.artist_id == query['artist'][0], schema.Album.label_id == query['filter_value'][0])
        elif query['filter'][0] == u'grouping':
            albums = schema.Album.select().join(schema.Track).where(schema.Album.artist_id == query['artist'][0], schema.Track.grouping == query['filter_value'][0]).distinct()
        elif query['filter'][0] == u'samplerate':
            albums = schema.Album.select().join(schema.Track).where(schema.Album.artist_id == query['artist'][0], schema.Track.samplerate == query['filter_value'][0]).distinct()
        elif query['filter'][0] == u'format':
            albums = schema.Album.select().join(schema.Track).where(schema.Album.artist_id == query['artist'][0], schema.Track.format == query['filter_value'][0]).distinct()
        elif query['filter'][0] == u'added_at':
            albums = schema.Album.select().join(schema.Track).where(schema.Album.artist_id == query['artist'][0], schema.Track.added == query['filter_value'][0]).distinct()
        elif query['filter'][0] == u'year':
            albums = schema.Album.select().where(schema.Album.artist_id == query['artist'][0], schema.Album.original_year == query['filter_value'][0])
        else:
            albums = schema.Album.select().where(schema.Album.artist_id == query['artist'][0])
        for album in sorted(albums, key=lambda x: x.original_year):
            yield Ref.directory(
                uri=uricompose('bigbeet',
                                None,
                                'tracks',
                                dict(album=album.id,
                                     filter=query['filter'][0],
                                     filter_value=query['filter_value'][0]
                                     )),
                    name="{0} {1} ({2})".format(
                        (album.original_year or album.year or ''),
                        album.name,
                        album.tracktotal))


    def _browse_tracks(self, query):
        if query['filter'][0] == u'samplerate':
            tracks = schema.Track.select().where(schema.Track.album_id == query['album'][0], schema.Track.samplerate == query['filter_value'][0])
        elif query['filter'][0] == u'grouping':
            tracks = schema.Track.select().where(schema.Track.album_id == query['album'][0], schema.Track.grouping == query['filter_value'][0])
        elif query['filter'][0] == u'format':
            tracks = schema.Track.select().where(schema.Track.album_id == query['album'][0], schema.Track.format == query['filter_value'][0])
        else:
            tracks = schema.Track.select().where(schema.Track.album_id == query['album'][0])
        for track in sorted(tracks, key=lambda x: x.track):
            yield Ref.track(
                uri="bigbeet:track:%s:%s" % (
                    track.id,
                    uriencode(str(track.path), '/')),
                name=track.name)

    def _browse_singletons(self, query):
        single_tracks = schema.Track.select().where(schema.Track.album_id == None)
        groupings = set([s.grouping for s in single_tracks])
        for grouping in sorted(groupings):
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'singleton_tracks',
                                   dict(grouping=grouping)),
                    name=grouping if bool(grouping) else u'No Group')

    def _browse_singleton_tracks(self, query):
        single_tracks = schema.Track.select().where(schema.Track.grouping == query['grouping'][0], schema.Track.album_id == None)
        for track in sorted(single_tracks, key=lambda x: x.artist):
            yield Ref.track(
                uri="bigbeet:track:%s:%s" % (
                    track.id,
                    uriencode(str(track.path), '/')),
                name="{0} - {1}".format(track.artist,track.name))

    def _browse_compilations(self, query):
        comp_albums = schema.Album.select().where(schema.Album.comp == 1).order_by(schema.Album.name)
        for album in comp_albums:
            yield Ref.album(
                uri=uricompose('bigbeet',
                               None,
                               'tracks',
                               dict(album=album.id, filter=u'album')),
                name="{0} ({1})".format(
                    album.name,
                    album.tracktotal))

    def _browse_labels(self, query):
        labels = schema.Label.select().order_by(schema.Label.name)
        for label in labels:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(label=label.id, filter=u'label')),
                    name=label.name)

    def _browse_format(self, query):
        formats = schema.Track.select(schema.Track.format).distinct()
        for f0rmat in formats:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(format=f0rmat.format, filter=u'format')),
                    name=f0rmat.format)

    def _browse_samplerate(self, query):
        samplerates = schema.Track.select(schema.Track.samplerate).distinct().order_by(schema.Track.samplerate.desc())
        for samplerate in samplerates:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(samplerate=samplerate.samplerate,
                                        filter=u'samplerate')),
                    name="{}kbps".format(samplerate.samplerate/1000.0))

    def _browse_year(self, query):
        years = schema.Album.select(schema.Album.original_year).distinct().order_by(schema.Album.original_year.desc())
        for year in years:
            yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(year=year.original_year, filter=u'year')),
                    name=str(year.original_year))

    def _browse_added_at(self, query):
        import pdb; pdb.set_trace()
        adds = schema.Track.select(schema.Track.added).distinct().order_by(schema.Track.added.desc())
        addeds = [datetime.datetime.fromtimestamp(add.added).strftime('%Y-%m') for add in adds]
        for added in set(addeds):
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(added=added.added,
                                        filter=u'added_at')),
                    name="{}".format(added))

    def browse(self, uri):
        logger.info(u"Browse being called for %s" % uri)
        level = urisplit(uri).path
        query = self._sanitize_query(dict(urisplit(uri).getquerylist()))
        # import pdb; pdb.set_trace()
        logger.debug("Got parsed to level: %s - query: %s" % (level,
                                                              query))
        result = []
        if not level:
            logger.error("No level for uri %s" % uri)
                # import pdb; pdb.set_trace()
        if level == 'root':
           return list(self._browse_root())
        elif level == "genre":
            return list(self._browse_genre(query))
        elif level == "grouping":
            return list(self._browse_groupings(query))
        elif level == "artists":
            return list(self._browse_artists(query))
        elif level == "albums":
            return list(self._browse_albums(query))
        elif level == "tracks":
            return list(self._browse_tracks(query))
        elif level == "singletons":
            return list(self._browse_singletons(query))
        elif level == "singleton_tracks":
            return list(self._browse_singleton_tracks(query))
        elif level == "compilations":
            return list(self._browse_compilations(query))
        elif level == "label":
            return list(self._browse_labels(query))
        elif level == "format":
            return list(self._browse_format(query))
        elif level == "samplerate":
            return list(self._browse_samplerate(query))
        elif level == "year":
            return list(self._browse_year(query))
        elif level == "added%20at":
            return list(self._browse_added_at(query))
        else:
            logger.debug('Unknown URI: %s', uri)
        return result


    def get_distinct(self, field, query=None):
        """
        used by mpd clients like ncmpcpp
        """
        logger.warn(u'get_distinct called field: %s, Query: %s' % (field,
                                                                   query))
        query = self._sanitize_query(query)
        logger.debug(u'Search sanitized query: %s ' % query)
        result = []
        if field == 'artist':
            result = schema.Artist.select().order_by(schema.Artist.name)
        elif field == 'genre':
            result = schema.Genre.select().order_by(schema.Genre.name)
        else:
            logger.info(u'get_distinct not fully implemented yet')
            import pdb; pdb.set_trace()
            result = []
        return set([v.name for v in result])

    def lookup(self, uri):
        logger.info(u'looking up uri = %s of type %s' % (
            uri.encode('ascii', 'ignore'), type(uri).__name__))
        item_type, item_id, item_path = self.backend._extract_uri(uri)
        logger.debug('item_type: "%s", item_id: "%s"' % (item_type, item_id))
        if item_type == 'track':
            try:
                track = self._get_track(item_id)
                return [track]
            except Exception as error:
                logger.debug(u'Failed to lookup "%s": %s' % (uri, error))
                import pdb; pdb.set_trace()
                return []
        elif item_type == 'album':
            try:
                tracks = self._get_album(item_id)
                return tracks
            except Exception as error:
                logger.debug(u'Failed to lookup "%s": %s' % (uri, error))
                return []
        else:
            logger.debug(u"Dont know what to do with item_type: %s" %
                         item_type)
            return []

    def _get_track(self, item_id):
        track = schema.Track.get(schema.Track.id == int(item_id))
        return self._convert_track(track)

    def _get_album(self, item_id):
        album = schema.Album.get(schema.Album.id == item_id)
        return [self._convert_track(track) for track in album.track_set]

    def _sanitize_query(self, query):
        """
        We want a consistent query structure that later code
        can rely on
        """
        # import pdb; pdb.set_trace()
        if not query:
            return query
        for (key, values) in query.iteritems():
            if not values:
                del query[key]
            if type(values) is not list:
                query[key] = [values]
            for index, value in enumerate(values):
                if key == 'date':
                    year = self._sanitize_year(str(value))
                    if year:
                        query[key][index] = year
                    else:
                        del query[key][index]
                    # we possibly could introduce query['year'],
                    # query['month'] etc.
                    # Maybe later
        return query

    def _sanitize_year(self, datestr):
        """
        Clients may send date field as Date String, Year or Zero
        """
        try:
            year = str(datetime.datetime.strptime(datestr, '%Y').date().year)
        except:
            try:
                year = str(datetime.datetime.strptime(datestr,
                                                      '%Y-%m-%d').date().year)
            except:
                year = None
        return year

    def _build_date(self, year, month, day):
        month = 1 if month == 0 else month
        day = 1 if day == 0 else day
        try:
            d = datetime.datetime(
                year,
                month,
                day)
            date = '{:%Y-%m-%d}'.format(d)
        except:
            date = None
        return date

    def _build_query_expressions(self, query, exact):
        """
        Transforms a mopidy query into a list of bigbeet
        query expressions
        """
        # So far no mopidy clients uses a list of expressions in a query
        # therefore we only take the first element
        bb_query = []
        schemas = []
        if u'album' in query:
            if exact:
                bb_query.append(schema.Album.name == query['album'][0])
            else:
                bb_query.append(schema.Album.name.contains(query['album'][0]))
            schemas.append(u'album')
        if u'performer' in query:
            if exact:
                bb_query.append(schema.Track.artist == query['performer'][0])
            else:
                bb_query.append(schema.Track.artist.contains(query['performer'][0]))
            schemas.append(u'track')
        if u'artist' in query:
            if exact:
                bb_query.append(schema.Artist.name == query['artist'][0])
            else:
                bb_query.append(schema.Artist.name.contains(query['artist'][0]))
            schemas.append(u'artist')
        if u'uri' in query:
            if exact:
                bb_query.append(schema.Track.path == query['uri'][0])
            else:
                bb_query.append(schema.Track.path.contains(query['uri'][0]))
            schemas.append(u'track')
        if u'date' in query:
            import pdb; pdb.set_trace()
            bb_query.append(schema.Track.year == int(query['year'][0]))
            schemas.append(u'track')
        if u'track_name' in query:
            if exact:
                bb_query.append(schema.Track.name == query['track_name'][0])
            else:
                bb_query.append(schema.Track.name.contains(query['track_name'][0]))
            schemas.append(u'track')
        if u'composer' in query:
            if exact:
                bb_query.append(schema.Track.composer == query['composer'][0])
            else:
                bb_query.append(schema.Track.composer.contains(query['composer'][0]))
            schemas.append(u'track')
        if u'genre' in query:
            if exact:
                bb_query.append(schema.Genre.name == query['genre'][0])
            else:
                bb_query.append(schema.Genre.name.contains(query['genre'][0]))
            schemas.append(u'genre')
        if u'any' in query:
            if exact:
                bb_query.append((schema.Album.name == query['album'][0]) |
                    (schema.Track.artist == query['performer'][0]) |
                    (schema.Artist.name == query['artist'][0]) |
                    (schema.Track.path == query['uri'][0]) |
                    (schema.Track.year == int(query['year'][0])) |
                    (schema.Track.name == query['track_name'][0]) |
                    (schema.Track.composer == query['composer'][0]) |
                    (schema.Genre.name == query['genre'][0]))
            else:
                bb_query.append((schema.Album.name.contains(query['album'][0])) |
                    (schema.Track.artist.contains(query['performer'][0])) |
                    (schema.Artist.name.contains(query['artist'][0])) |
                    (schema.Track.path.contains(query['uri'][0])) |
                    (schema.Track.year == int(query['year'][0])) |
                    (schema.Track.name.contains(query['track_name'][0])) |
                    (schema.Track.composer.contains(query['composer'][0])) |
                    (schema.Genre.name.contains(query['genre'][0])))
            [schemas.append(i) for i in ['track','album','artist','genre']]
        return (set(schemas), bb_query)

    def _build_joins(self, schemas, query_type):
        """
        Build a joined Expression
        """
        if query_type == u'album':
            join_schema = schema.Album.select()
            if u'track' in schemas:
                join_schema = join_schema.join(schema.Track)
        else:
            join_schema = schema.Track.select()
            if schemas != set([u'track']):
                join_schema = join_schema.join(schema.Album)
        if u'artist' in schemas:
            join_schema = join_schema.join(schema.Artist)
        if u'genre' in schemas:
            join_schema = join_schema.join(schema.Genre)
        return join_schema

    def _convert_track(self, item):
        """
        Transforms a track item into a mopidy Track
        """
        # import pdb; pdb.set_trace()
        if not item:
            return
        track_kwargs = {}
        album_kwargs = {}
        artist_kwargs = {}
        albumartist_kwargs = {}

        track_kwargs['name'] = item.name
        track_kwargs['track_no'] = item.track
        track_kwargs['disc_no'] = item.disc
        track_kwargs['genre'] = item.genre
        track_kwargs['comment'] = item.comments
        track_kwargs['bitrate'] = item.bitrate
        track_kwargs['last_modified'] = int(item.mtime * 1000)
        if self.backend.use_original_release_date:
            track_kwargs['date'] = self._build_date(
                                       item.original_year,
                                       item.original_month,
                                       item.original_day)
        else:
             track_kwargs['date'] = self._build_date(
                                       item.year,
                                       item.month,
                                       item.day)
        track_kwargs['musicbrainz_id'] = item.mb_trackid
        track_kwargs['uri'] = "bigbeet:track:%s:%s" % (
                item.id,
                uriencode(str(item.path), '/'))
        track_kwargs['length'] = int(item.length) * 1000

        album = item.album
        if not album or album.comp:
        # singleton or compilations
            artist_kwargs['name'] = item.artist
            track_kwargs['artists'] = [Artist(**artist_kwargs)]
        else:
            album_kwargs['name'] = album.name
            album_kwargs['musicbrainz_id'] = album.mb_albumid
            album_kwargs['num_tracks'] = album.tracktotal
            track_kwargs['album'] = Album(**album_kwargs)
            artist = album.artist
            if artist:
                album_kwargs['name'] = album.name
                album_kwargs['musicbrainz_id'] = album.mb_albumid
                artist_kwargs['name'] = artist.name
                artist_kwargs['musicbrainz_id'] = artist.mb_albumartistid
                track_kwargs['artists'] = [Artist(**artist_kwargs)]
        return Track(**track_kwargs)

    def _convert_album(self, album):
        """
        Transforms a beets album into a mopidy Track
        """
        if not album:
            return
        album_kwargs = {}
        artist_kwargs = {}

        album_kwargs['name'] = album.name
        album_kwargs['num_discs'] = album.disctotal
        album_kwargs['num_tracks'] = album.tracktotal
        album_kwargs['musicbrainz_id'] = album.mb_albumid
        album_kwargs['date'] = None
        if self.backend.use_original_release_date:
                album_kwargs['date'] = self._build_date(
                                            album.original_year,
                                            album.original_month,
                                            album.original_day)
        else:
                album_kwargs['date'] = self._build_date(album.year,
                                                        album.month,
                                                        album.day)

        # if 'added' in item:
        #    album_kwargs['last_modified'] = album['added']

        # if 'artpath' in album:
        #    album_kwargs['images'] = [album['artpath']]
        artist_kwargs['name'] = album.artist.name
        artist_kwargs['musicbrainz_id'] = album.artist.mb_albumartistid
        artist = Artist(**artist_kwargs)
        album_kwargs['artists'] = [artist]
        album_kwargs['uri'] = uricompose('bigbeet',
                                         None,
                                         ("album:%s:%s" % (album.id,album.mb_albumid)),
                                         None)
        album = Album(**album_kwargs)
        return album
