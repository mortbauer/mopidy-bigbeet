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


class BigbeetLibraryProvider(backend.LibraryProvider):
    ROOT_URI = 'bigbeet:root'
    root_directory = Ref.directory(uri=ROOT_URI, name='Local (bigbeet)')
    TRACK_ATTRIBUTES = {u'track_name': u'name', }

    def __init__(self, *args, **kwargs):
        super(BigbeetLibraryProvider, self).__init__(*args, **kwargs)
        # schema.connect_db(self.backend.db_path)
        try:
            schema.connect_db(self.backend.db_path)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            pass

    def search(self, query=None, uris=None, exact=False):
        logger.info(u'Search query: %s in uris: %s' % (query, uris))
        # query = self._sanitize_query(query)
        # logger.debug(u'Search sanitized query: %s ' % query)
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

    def browse(self, uri):
        logger.debug(u"Browse being called for %s" % uri)
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
            for item in schema.Genre.select().where(schema.Genre.parent == None).order_by(schema.Genre.name):
                result.append(Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'genre',
                                   dict(genre=item.id)),
                    name=item.name if bool(item.name) else u'No Genre'))
        elif level == "genre":
            # import pdb; pdb.set_trace()
            genre = schema.Genre.get(schema.Genre.id == int(query['genre'][0]))
            subgenres = schema.Genre.select().where(
                schema.Genre.parent == genre.id).execute()
            # artist refs not browsable via mpd
            for subgenre in subgenres:
                result.append(Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'genre',
                                   dict(genre=subgenre.id)),
                    name=subgenre.name
                ))
            for artist in genre.artists.execute():
                result.append(Ref.directory(
                    uri=uricompose('bigbeet',
                                   None,
                                   'artist',
                                   dict(artist=artist.id)),
                    name=artist.name
                    ))
        elif level == "artist":
            artist = schema.Artist.get(schema.Artist.id == int(query['artist'][0]))
            for album in artist.albums:
                result.append(Ref.album(
                    uri=uricompose('bigbeet',
                                   None,
                                   'album',
                                   dict(album=album.id)),
                    name=album.name))
        elif level == "album":
            album = schema.Album.get(schema.Album.id == int(query['album'][0]))
            # import pdb; pdb.set_trace()
            for track in album.track_set:
                result.append(Ref.track(
                    uri="bigbeet:track:%s:%s" % (
                        track.id,
                        uriencode(str(track.path), '/')),
                    name=track.name))
        else:
            logger.debug('Unknown URI: %s', uri)
        return result

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

    def get_distinct(self, field, query=None):
        logger.warn(u'get_distinct called field: %s, Query: %s' % (field,
                                                                   query))
        logger.info(u'get_distinct not implemented yet')
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
        album = item.album
        artist = album.artist
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
        # TODO
        #if 'tracktotal' in item:
        #    album_kwargs['num_tracks'] = int(item['tracktotal'])

        album_kwargs['name'] = album.name
        album_kwargs['musicbrainz_id'] = album.mb_albumid
        
        artist_kwargs['name'] = artist.name
        artist_kwargs['musicbrainz_id'] = artist.mb_albumartistid
        #    albumartist_kwargs['name'] = item['artist']

        #if 'albumartist' in item:
        #    albumartist_kwargs['name'] = item['albumartist']
        track_kwargs['artists'] = [Artist(**artist_kwargs)]
        track_kwargs['album'] = Album(**album_kwargs)
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
        # album_kwargs['num_tracks'] = album.tracktotal
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
