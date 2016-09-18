from __future__ import unicode_literals
from playhouse.migrate import *
from mopidy_bigbeet.schema import schema

#my_db = SqliteDatabase('my_database.db')
#migrator = SqliteMigrator(my_db)

#title_field = CharField(default='')
#status_field = IntegerField(null=True)

#migrate(
#    migrator.add_column('some_table', 'title', title_field),
#    migrator.add_column('some_table', 'status', status_field),
#    migrator.drop_column('some_table', 'old_column'),
#)
class Migration():

    def __init__(self, *args, **kwargs):
        self.migrator = SqliteMigrator(kwargs.get(u'database'))


    def migrate_db(self):
        with schema.database.transaction():
            migrate(self.migrator.add_column('tracks', 'beets_id',
                                             IntegerField(null=True)),
                    self.migrator.add_column('albums', 'beets_id',
                                             IntegerField(null=True)),
                    self.migrator.add_column('albums', 'tracktotal',
                                             IntegerField(null=True))
                )
            schema.SchemaMigration.create(version = '20160913' )

    def update_db(self):

        items = schema.bdb.items()
        for item in items:
            try:
                track, created = schema.Track.get_or_create(
                    name = item.title,
                    path = item.path)
                track.beets_id = item.id
                track.save()
                bdb_album = item.get_album()
                if bdb_album:
                    album = track.album
                    album.beets_id = bdb_album.id
                    album.tracktotal = len(bdb_album.items())
                    album.save()
                else:
                    track.acoustid_fingerprint = item.acoustid_fingerprint
                    track.acoustid = item.acoustid_id
                    track.added = item.added
                    track.artist = item.artist
                    track.asin = item.asin
                    track.bitdepth = item.bitdepth
                    track.bitrate = item.bitrate
                    track.beets_id = item.id
                    track.bpm = item.bpm
                    track.channels = item.channels
                    track.comments = item.comments
                    track.composer = item.composer
                    track.country = item.country
                    track.day = item.day
                    track.disc = item.disc
                    track.encoder = item.encoder
                    track.format = item.format
                    track.genre = item.genre
                    track.grouping = item.grouping
                    track.language = item.language
                    track.length = item.length
                    track.mb_releasegroupid = item.mb_releasegroupid
                    track.mb_trackid = item.mb_trackid
                    track.media = item.media
                    track.month = item.month
                    track.mtime = item.mtime
                    track.original_day = item.original_day
                    track.original_month = item.original_month
                    track.original_year = item.original_year
                    track.samplerate = item.samplerate
                    track.track = item.track
                    track.year = item.year
                    track.save()
            except:
                import pdb; pdb.set_trace()
