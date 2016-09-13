from __future__ import unicode_literals
import os.path
from peewee import *
from playhouse.apsw_ext import APSWDatabase
from mopidy_bigbeet import Extension
from mopidy_bigbeet.schema import beet_schema, genre_schema

user_version = 1
# database = SqliteDatabase(None, pragmas=(
#                                     ('journal_mode', 'WAL'),
#                                     ('user_version', user_version)
#                                     ))

# database = MySQLDatabase('bigbeet', user='rails_user', passwd='tequila' charset='utf8mb4')

database = APSWDatabase(None,
                        pragmas = (
                                ('temp_store', 2),
                                ('journal_mode', 'WAL'),
                                ('user_version', user_version)
                                    ))

def setup_db():
	# import pdb; pdb.set_trace()
    try:
        database.drop_tables([Genre, AlbumGroup, Album, ArtistSecondaryGenre, Artist, Label, SecondaryGenre, Track])
    except:
        pass
    database.create_tables([Genre, AlbumGroup, Album, ArtistSecondaryGenre, Artist, Label,SecondaryGenre,Track])

def connect_db(db_path):
    global database
    database.init(db_path)
    database.connect()

def migrate_db():
    print "This needs to be build"

def check_db(data_dir):
	db_path = os.path.join(data_dir, b'library.db')
	db_existed = os.path.isfile(db_path)
        connect_db(db_path)
        if not db_existed:
            setup_db()
        elif dict(database._pragmas)['user_version'] != user_version:
            migrate_db()

def check_genres(config):
    data_dir = Extension.get_data_dir(config)
    bdb = beet_schema.BeetsLibrary(config['bigbeet']['beetslibrary']).lib
    gdb = genre_schema.GenreTree(data_dir)
    albums = bdb.albums()
    for album in albums:
        gdb.find_missing(album['genre'])
    for item in bdb.items():
        gdb.find_missing(album['genre'])
    with open(os.path.join(data_dir, 'genres-missing.txt'), 'w') as outfile:
        for mg in set(gdb.genres_missing):
            print mg
            outfile.write(mg + '\n')
    print set(gdb.genres_missing)


def scan(config):
        data_dir = Extension.get_data_dir(config)
        import pdb; pdb.set_trace()
        bdb = beet_schema.BeetsLibrary(config['bigbeet']['beetslibrary']).lib
        gdb = genre_schema.GenreTree(data_dir)
        db_path = os.path.join(data_dir, b'library.db')
        connect_db(db_path)
        #import pdb; pdb.set_trace()
        for bdb_album in bdb.albums():
            print("%s - %s" % (bdb_album.id, bdb_album.album))
            genre_name = bdb_album['genre']
            genres = gdb.find_parents(genre_name)
            parent_id = None
            while genres:
                genre_name = genres.pop()
                genre, created = Genre.get_or_create(name=genre_name.title(), parent=parent_id)
                parent_id = genre.id
            artist, created = Artist.get_or_create(name=bdb_album.albumartist, mb_albumartistid=bdb_album.mb_albumartistid)
            artist.country = bdb_album.country
            artist.albumartist_sort = bdb_album.albumartist_sort
            artist.albumartist_credit = bdb_album.albumartist_credit
            artist.genre = genre
            artist.save()
            label, created = Label.get_or_create(name = bdb_album.label)
            album_group, created = AlbumGroup.get_or_create(name = bdb_album.albumtype)
            album, created = Album.get_or_create(name = bdb_album.album, mb_albumid = bdb_album.mb_albumid)
            album.label = label
            album.artist = artist
            album.album_group = album_group
            album.albumstatus = bdb_album.albumstatus
            album.catalognum = bdb_album.catalognum
            album.comp = bdb_album.comp
            album.day = bdb_album.day
            album.disctotal = bdb_album.disctotal
            album.genre = genre
            album.language = bdb_album.language
            album.mb_albumid = bdb_album.mb_albumid
            album.mb_releasegroupid = bdb_album.mb_releasegroupid
            album.month = bdb_album.month
            album.original_day = bdb_album.original_day
            album.original_month = bdb_album.original_month
            album.original_year = bdb_album.original_year
            album.year = bdb_album.year
            album.save()
            for item in bdb_album.items():
                track, created = Track.get_or_create(name = item.title, path = item.path)
                track.acoustid_fingerprint = item.acoustid_fingerprint
                track.acoustid = item.acoustid_id
                track.added = item.added
                track.album = album
                track.artist = item.artist
                track.asin = item.asin
                track.bitdepth = item.bitdepth
                track.bitrate = item.bitrate
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


	# check_db(config)
	pass

class BaseModel(Model):
    created_at = DateTimeField(null=True)
    updated_at = DateTimeField(null=True)
    class Meta:
        database = database

class AlbumGroup(BaseModel):
    name = CharField(null=True)  # varchar
    class Meta:
        db_table = 'album_groups'

class Genre(BaseModel):
    name = CharField(null=True)  # varchar
    parent = IntegerField(null=True)
    class Meta:
        db_table = 'genres'

class Label(BaseModel):
    name = CharField(null=True)  # varchar
    class Meta:
        db_table = 'labels'

class Artist(BaseModel):
    albumartist_credit = TextField(null=True)
    albumartist_sort = CharField(null=True)  # varchar
    country = CharField(null=True)  # varchar
    genre = ForeignKeyField(Genre, related_name='artists', db_column='genre_id', null=True)
    mb_albumartistid = CharField(null=True)  # varchar
    name = CharField(null=True)  # varchar
    class Meta:
        db_table = 'artists'

class Album(BaseModel):
    added = FloatField(null=True)  # float
    album_group = ForeignKeyField(AlbumGroup, related_name='albums', db_column='album_group_id', null=True)
    albumstatus = CharField(null=True)  # varchar
    artist = ForeignKeyField(Artist, related_name='albums', db_column='artist_id', null=True)
    catalognum = CharField(null=True)  # varchar
    comp = IntegerField(null=True)
    day = IntegerField(null=True)
    disctotal = IntegerField(null=True)
    genre = ForeignKeyField(Genre, related_name='albums', db_column='genre_id', null=True)
    label = ForeignKeyField(Label, related_name='albums', db_column='label_id', null=True)
    language = CharField(null=True)  # varchar
    mb_albumid = CharField(null=True)  # varchar
    mb_releasegroupid = CharField(null=True)  # varchar
    month = IntegerField(null=True)
    name = CharField(null=True)  # varchar
    # tracktotal = IntegerField(null=True)
    original_day = IntegerField(null=True)
    original_month = IntegerField(null=True)
    original_year = IntegerField(null=True)
    year = IntegerField(null=True)
    class Meta:
        db_table = 'albums'

class SecondaryGenre(BaseModel):
    name = CharField(null=True)  # varchar
    class Meta:
        db_table = 'secondary_genres'

class ArtistSecondaryGenre(BaseModel):
    artist = ForeignKeyField(Artist, db_column='artist_id', null=True)
    position = IntegerField(null=True)
    secondary_genre = ForeignKeyField(SecondaryGenre, db_column='secondary_genre_id', null=True)
    class Meta:
        db_table = 'artist_secondary_genres'

class SchemaMigration(BaseModel):
    version = CharField(primary_key=True)  # varchar
    class Meta:
        db_table = 'schema_migrations'


class Track(BaseModel):
    acoustid_fingerprint = CharField(null=True)  # varchar
    acoustid = CharField(db_column='acoustid_id', null=True)  # varchar
    added = FloatField(null=True)  # float
    album = ForeignKeyField(Album, db_column='album_id', null=True)
    artist = CharField(null=True)  # varchar
    asin = CharField(null=True)  # varchar
    bitdepth = IntegerField(null=True)
    bitrate = IntegerField(null=True)
    bpm = IntegerField(null=True)
    channels = IntegerField(null=True)
    comments = CharField(null=True)  # varchar
    composer = CharField(null=True)  # varchar
    country = CharField(null=True)  # varchar
    day = IntegerField(null=True)
    disc = IntegerField(null=True)
    encoder = CharField(null=True)  # varchar
    format = CharField(null=True)  # varchar
    genre = CharField(null=True)  # varchar
    grouping = CharField(null=True)  # varchar
    language = CharField(null=True)  # varchar
    length = FloatField(null=True)  # float
    mb_releasegroupid = CharField(null=True)  # varchar
    mb_trackid = CharField(null=True)  # varchar
    media = CharField(null=True)  # varchar
    month = IntegerField(null=True)
    mtime = FloatField(null=True)  # float
    name = CharField(null=True)  # varchar
    original_day = IntegerField(null=True)
    original_month = IntegerField(null=True)
    original_year = IntegerField(null=True)
    path = BlobField(null=True)
    samplerate = IntegerField(null=True)
    track = IntegerField(null=True)
    year = IntegerField(null=True)
    class Meta:
        db_table = 'tracks'
