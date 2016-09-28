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
# - search genre include children genres
# - limit search results
# - show Singletons below Genre (Volksmusik)
# - Root Classic composer gernre = classical music + childs


class BigbeetLibraryProvider(backend.LibraryProvider):
    ROOT_URI = 'bigbeet:root'
    root_directory = Ref.directory(uri=ROOT_URI, name='Local (bigbeet)')
    FIRST_LEVEL = [
        'Genre',
        'Grouping',
        'Radio Plays',
        'Singletons',
        'Compilations',
        'Label',
        'Format',
        'Samplerate',
        'Year',
        # 'Added At',
    ]
    auto_grouping = 0


    def __init__(self, *args, **kwargs):
        super(BigbeetLibraryProvider, self).__init__(*args, **kwargs)
        # schema.connect_db(self.backend.db_path)
        try:
            schema._initialize(self.backend.config)
            self.auto_grouping = 10
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
        if query and 'genre_id' in query:
            genre_id = query['genre_id'][0]
            genre = schema.Genre.get(id=genre_id)
            artists = genre.artists
            if self.auto_grouping and len(artists) > self.auto_grouping:
                for ref in self._show_groupings(query, u'artists'):
                    yield ref
            subgenres = schema.Genre.select().where(
                schema.Genre.parent == genre_id)
            if subgenres:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(all_artists='1',
                                        genre_id=genre_id)),
                    name="All Artists"
                )
            for subgenre in subgenres:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'genre',
                                   dict(genre_id=subgenre.id)),
                    name="- {}".format(subgenre.name)
                )
            for comp_album in self._show_compilations(query):
                yield comp_album
            for artist in artists:
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'albums',
                                   dict(artist_id=artist.id)),
                    name=artist.name
                    )
        else:
            for genre in schema.Genre.select().where(schema.Genre.parent == None).order_by(schema.Genre.name):
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'genre',
                                   dict(genre_id=genre.id)),
                    name=genre.name if bool(genre.name) else u'No Genre')

    def _show_groupings(self, query, level):
        groupings = self._get_groupings(query)
        refs = []
        query_dict = dict([(k, v[0]) for k,v in query.iteritems()])
        for grouping in groupings:
            query_dict['grouping'] = grouping
            refs.append(Ref.directory(
                uri=uricompose('bigbeet',
                                None,
                                level,
                                query_dict),
                name=": {0}".format(grouping))
            )
        return refs


    def _browse_groupings(self, query):
        groupings = self._show_groupings(query, 'artists')
        for g in groupings:
            yield g

    def _browse_radio_plays(self, query):
        radio_plays = schema.Track.select().where(schema.Track.genre == 'Radio Play')
        for grouping in filter(bool,set(h.grouping for h in radio_plays)):
            yield Ref.directory(
                uri=uricompose('bigbeet',
                                None,
                                'tracks',
                                dict(grouping=grouping,
                                     track_genre='Radio Play')),
                    name=grouping)


    def _browse_artists(self, query):
        if u'all_artists' in query:
            genre = schema.Genre.get(id=query['genre_id'][0])
            # import pdb; pdb.set_trace()
            genres = schema._find_children(genre,[genre])
            logger.info([g.name for g in genres])
            artists = []
            for genre in genres:
                artists += [a for a in schema.Artist.select().where(schema.Artist.genre_id == genre.id)]
        else:
            schemas, bb_query = self._build_query_expressions( query, True)
            joined_schema = self._build_joins(schemas, u'artist')
            artists = joined_schema.where(*bb_query).distinct()
        if self.auto_grouping and len(artists) > self.auto_grouping:
                for ref in self._show_groupings(query, u'artists'):
                    yield ref
        query_dict = dict([(k, v[0]) for k,v in query.iteritems()])
        for artist in sorted(artists, key=lambda x: x.name):
            query_dict['artist_id'] = artist.id
            yield Ref.directory(
                uri=uricompose('bigbeet',
                                None,
                                'albums',
                                query_dict),
                name=artist.name
                )


    def _browse_albums(self, query):
        if u'artist_id' in query:
            query.pop('genre_id', None)
        schemas, bb_query = self._build_query_expressions( query, True)
        joined_schema = self._build_joins(schemas, u'album')
        albums = joined_schema.where(*bb_query).distinct()
        query_dict = dict([(k, v[0]) for k,v in query.iteritems()])
        if self.auto_grouping and len(albums) > self.auto_grouping:
                for ref in self._show_groupings(query, u'albums'):
                    yield ref
        for album in sorted(albums, key=lambda x: x.original_year):
            query_dict['album_id'] = album.id
            yield Ref.directory(
                uri=uricompose('bigbeet',
                                None,
                                'tracks',
                                query_dict),
                    name="{0} {1} ({2})".format(
                        (album.original_year or album.year or ''),
                        album.name,
                        album.tracktotal))


    def _browse_tracks(self, query):
        schemas, bb_query = self._build_query_expressions( query, True)
        joined_schema = self._build_joins(schemas, u'track')
        tracks = joined_schema.where(*bb_query).distinct()
        for track in sorted(tracks, key=lambda x: x.track):
            yield Ref.track(
                uri="bigbeet:track:%s:%s" % (
                    track.id,
                    uriencode(str(track.path), '/')),
                name=track.name)

    def _browse_singletons(self, query):
        groupings = self._show_groupings({u'singleton': '1'},'singleton_tracks')
        for g in groupings:
            yield g

    def _browse_singleton_tracks(self, query):
        single_tracks = schema.Track.select().where(schema.Track.grouping == query['grouping'][0], schema.Track.album_id == None)
        for track in sorted(single_tracks, key=lambda x: x.artist):
            yield Ref.track(
                uri="bigbeet:track:%s:%s" % (
                    track.id,
                    uriencode(str(track.path), '/')),
                name="{0} - {1}".format(track.artist,track.name))

    def _show_compilations(self, query):
        refs = []
        if u'genre_id' in query:
            comp_albums = schema.Album.select().where(schema.Album.comp == 1, schema.Album.genre_id == query['genre_id'][0]).order_by(schema.Album.name)
        else:
            comp_albums = schema.Album.select().where(schema.Album.comp == 1).order_by(schema.Album.name)
        for album in comp_albums:
            refs.append(Ref.album(
                uri=uricompose('bigbeet',
                               None,
                               'tracks',
                               dict(album_id=album.id)),
                name="= {0} ({1})".format(
                    album.name,
                    album.tracktotal)))
        return refs

    def _browse_compilations(self, query):
        comp_albums = self._show_compilations(query)
        for ref in comp_albums:
            yield ref

    def _browse_labels(self, query):
        labels = schema.Label.select().order_by(schema.Label.name)
        for label in labels:
            if not label.name:
                continue
            yield Ref.directory(
                uri=uricompose('bigbeet',
                               None,
                               'artists',
                               dict(label=label.id)),
                name=label.name)

    def _browse_format(self, query):
        formats = schema.Track.select(schema.Track.format).distinct()
        for f0rmat in formats:
            if not f0rmat.format:
                continue
            yield Ref.directory(
                uri=uricompose('bigbeet',
                               None,
                               'artists',
                               dict(format=f0rmat.format)),
                name=f0rmat.format)

    def _browse_samplerate(self, query):
        samplerates = schema.Track.select(schema.Track.samplerate).distinct().order_by(schema.Track.samplerate.desc())
        for samplerate in samplerates:
            if not samplerate.samplerate:
                continue
            yield Ref.directory(
                uri=uricompose('bigbeet',
                               None,
                               'artists',
                               dict(samplerate=samplerate.samplerate)),
                name="{}kbps".format(samplerate.samplerate/1000.0))

    def _browse_year(self, query):
        years = schema.Album.select(schema.Album.original_year).distinct().order_by(schema.Album.original_year.desc())
        for year in years:
            yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(year=year.original_year)),
                    name=str(year.original_year))

    def _browse_added_at(self, query):
        adds = schema.Track.select(schema.Track.added).distinct().order_by(schema.Track.added.desc())
        addeds = [datetime.datetime.fromtimestamp(add.added).strftime('%Y-%m') for add in adds]
        for added in set(addeds):
                yield Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artists',
                                   dict(added=added.added)),
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
        elif level == "radio%20plays":
            return list(self._browse_radio_plays(query))
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

    def _get_groupings(self, query):
        groupings = []
        if query:
            if not 'grouping' in query:
                schemas, bb_query = self._build_query_expressions(query)
                logger.debug(query)
                joined_schema = schema.Track.select(schema.Track.grouping)
                if u'album' in schemas:
                    joined_schema = joined_schema.join(schema.Album)
                if u'artist' in schemas:
                    if not u'album' in schemas:
                        joined_schema = joined_schema.join(schema.Album)
                    joined_schema = joined_schema.join(schema.Artist)
                groupings = joined_schema.where(*bb_query).distinct()
        else:
            groupings = schema.Track.select(schema.Track.grouping).distinct()
        return sorted([g.grouping for g in groupings if g.grouping])


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

    def _build_query_expressions(self, query, exact=True):
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
        if u'album_id' in query:
            bb_query.append(schema.Track.album_id == query['album_id'][0])
            schemas.append(u'track')
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
        if u'artist_id' in query:
            bb_query.append(schema.Album.artist_id == query['artist_id'][0])
            schemas.append(u'album')
        if u'uri' in query:
            if exact:
                bb_query.append(schema.Track.path == query['uri'][0])
            else:
                bb_query.append(schema.Track.path.contains(query['uri'][0]))
            schemas.append(u'track')
        if u'date' in query:
            bb_query.append(schema.Track.year == int(query['year'][0]))
            schemas.append(u'track')
        if u'year' in query:
            bb_query.append(schema.Album.original_year == query['year'][0])
            schemas.append(u'album')
        if u'track_name' in query:
            if exact:
                bb_query.append(schema.Track.name == query['track_name'][0])
            else:
                bb_query.append(schema.Track.name.contains(query['track_name'][0]))
            schemas.append(u'track')
        if u'singleton' in query:
            bb_query.append(schema.Track.album_id == None)
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
        if u'genre_id' in query:
            bb_query.append(schema.Artist.genre_id == query['genre_id'][0])
            schemas.append(u'artist')
        if u'track_genre' in query:
            bb_query.append(schema.Track.genre == query['track_genre'][0])
            schemas.append(u'track')
        if u'grouping' in query:
            bb_query.append(schema.Track.grouping == query['grouping'][0])
            schemas.append(u'track')
        if u'label' in query:
            bb_query.append(schema.Album.label_id == query['label'][0])
            schemas.append(u'album')
        if u'format' in query:
            bb_query.append(schema.Track.format == query['format'][0])
            schemas.append(u'track')
        if u'samplerate' in query:
            bb_query.append(schema.Track.samplerate == query['samplerate'][0])
            schemas.append(u'track')
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
        logger.debug("query_type: %s, schemas: %s", query_type, "-".join(schemas))
        if query_type == u'artist':
            join_schema = schema.Artist.select()
            schemas -= set([u'artist'])
            if u'track' in schemas:
                schemas.update(['album'])
        elif query_type == u'album':
            schemas -= set([u'album'])
            join_schema = schema.Album.select()
        else:
            schemas -= set([u'track'])
            join_schema = schema.Track.select()
            if u'genre' in schemas:
                schemas.update(['artist'])
            if u'artist' in schemas:
                schemas.update(['album'])
        if u'album' in schemas:
            join_schema = join_schema.join(schema.Album)
        if u'artist' in schemas:
            join_schema = join_schema.join(schema.Artist)
        if u'track' in schemas:
            join_schema = join_schema.join(schema.Track)
        if u'genre' in schemas:
            join_schema = join_schema.join(schema.Genre)
        if u'label' in schemas:
            join_schema = join_schema.join(schema.Label)
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
