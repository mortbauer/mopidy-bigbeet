from __future__ import unicode_literals

import logging
import os.path
from os import listdir
from mopidy_bigbeet import Extension
from mopidy_bigbeet.schema import beet_schema, genre_schema
from peewee import *
from playhouse.apsw_ext import APSWDatabase, DateTimeField


user_version = 1
# database = SqliteDatabase(None, pragmas=(
#                                     ('journal_mode', 'WAL'),
#                                     ('user_version', user_version)
#                                     ))

# database = MySQLDatabase('bigbeet', user='rails_user', passwd='tequila'
# charset='utf8mb4')
logger = logging.getLogger(__name__)
bdb = None
gdb = None
data_dir = None
database = APSWDatabase(None,
                        pragmas=(
                                ('temp_store', 2),
                                ('journal_mode', 'WAL'),
                                ('user_version', user_version)
                                    ))


def _initialize(config):
    global bdb
    global gdb
    global data_dir
    data_dir = config['bigbeet']['bb_data_dir'] #|| Extension.get_data_dir(config)
    bdb = beet_schema.BeetsLibrary(config['bigbeet']['beetslibrary']).lib
    gdb = genre_schema.GenreTree(data_dir)
    db_path = os.path.join(data_dir, b'library.db')
    _connect_db(db_path)


def setup_db():
	# import pdb; pdb.set_trace()
    try:
        database.drop_tables(
            [Genre, AlbumGroup, Album, ArtistSecondaryGenre, Artist, Label, SecondaryGenre, SchemaMigration, Track])
    except:
        pass
    database.create_tables(
        [Genre, AlbumGroup, Album, ArtistSecondaryGenre, Artist, Label, SecondaryGenre, SchemaMigration, Track])
    SchemaMigration.create(version = '20160913' )


def _connect_db(db_path):
    global database
    db_existed = os.path.isfile(db_path)
    database.init(db_path)
    if not db_existed:
        setup_db()
    try:
        database.connect()
    except:
        pass
    _migrate_db()



def _migrate_db():
    migrations = listdir(os.path.join(
        os.path.dirname(__file__), '..', 'db', 'migrations'))
    migrations = set((m.split('.')[0] for m in migrations if m.startswith(u'migration')))
    versions = [v.version for v in SchemaMigration.select()]
    for migration in migrations:
        if not migration.split('_')[1] in versions:
            modul_name = 'mopidy_bigbeet.db.migrations.' + migration
            mig_object = __import__(modul_name,
                             globals(),
                             locals(),
                             [migration],
                             -1)
            mig = mig_object.Migration(database=database)
            # import pdb; pdb.set_trace()
            mig.migrate_db()
            mig.update_db()


def check_genres(config):
    _initialize(config)
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

def _sync_beets_item(track, item):
    track.name = item.title
    track.path = item.path
    track.acoustid_fingerprint = item.acoustid_fingerprint
    track.acoustid = item.acoustid_id
    track.added = item.added
    if item.singleton:
        track.album = None
    else:
        bdb_album = item.get_album()
        if bdb_album:
            track.album = Album.get(beets_id=item.get_album().id)
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


def _sync_beets_album(album, bdb_album):
    genre_name = bdb_album.genre or '_Unknown'
    genre = _set_genre(genre_name)
    artist, created = Artist.get_or_create(
        name=(bdb_album.albumartist or '_Unknown'),
        mb_albumartistid=bdb_album.mb_albumartistid)
    artist.country = bdb_album.country
    artist.albumartist_sort = bdb_album.albumartist_sort
    artist.albumartist_credit = bdb_album.albumartist_credit
    artist.genre = genre
    artist.save()
    label, created = Label.get_or_create(name = (bdb_album.label or '_Unknown'))
    album_group, created = AlbumGroup.get_or_create(
        name = (bdb_album.albumtype or '_Unknown'))
    album.name = bdb_album.album
    album.mb_albumid = bdb_album.mb_albumid
    album.label = label
    album.artist = artist
    album.album_group = album_group
    album.albumstatus = bdb_album.albumstatus
    album.beets_id = bdb_album.id
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
    album.tracktotal = len(bdb_album.items())
    album.year = bdb_album.year
    album.save()

def _set_genre(genre_name):
    genres = gdb.find_parents(genre_name)
    parent_id = None
    while genres:
        genre_name = genres.pop()
        genre, created = Genre.get_or_create(name=genre_name,
                                                 parent=parent_id)
        parent_id = genre.id
    return genre

def item_update(config,item_id):
    _initialize(config)
    item = bdb.get_item(item_id)
    if item:
        track, created = Track.get_or_create(beets_id=item_id)
        _sync_beets_item(track, item)
        logger.info(u'Track synced')
    else:
        tracks = Track.select().where(Track.beets_id == item_id)
        for track in tracks:
            logger.info(u'Track deleted: %s in %s', track.name, str(track.path))
            track.delete_instance()


def album_update(config,album_id):
    _initialize(config)
    bdb_album = bdb.get_album(album_id)
    if bdb_album:
        # import pdb; pdb.set_trace()
        album, created = Album.get_or_create(beets_id=bdb_album.id)
        _sync_beets_album(album, bdb_album)
        logger.info(u'Album synced: %s', album.name)
    else:
        albums = Album.select().where(Album.beets_id == album_id)
        for album in albums:
            artist = album.artist
            genre = artist.genre
            label = album.label
            album_group = album.album_group
            logger.info(u'Album deleted: %s', album.name)
            album.delete_instance()
            if not artist.albums:
                artist.delete_instance()
            if not label.albums:
                label.delete_instance()
            if not album_group.albums:
                album_group.delete_instance()
            if not genre.artists and not Genre.select().where(Genre.parent == genre.id):
                genre.delete_instance()


def _delete_orphans():
    albums = Album.select()
    for album in albums:
        if not album.track_set:
            album.delete_instance()
    artists = Artist.select()
    for artist in artists:
        if not artist.albums:
            artist.delete_instance()
    genres = Genre.select()
    for genre in genres:
        if not genre.artists:
            genre.delete_instance()
    labels = Label.select()
    for label in labels:
        if not label.albums:
            label.delete_instance()
    album_groups = AlbumGroup.select()
    for album_group in album_groups:
        if not album_group.albums:
            album_group.delete_instance()


def update(config):
    _initialize(config)
    # import pdb; pdb.set_trace()
    _delete_orphans()
    for item in bdb.items(u'singleton:true'):
        logger.info("update: %s", item.path)
        track, created = Track.get_or_create(beets_id=item.id)
        _sync_beets_item(track, item)

def _fix_mtime(config):
    _initialize(config)
    items = bdb.items()
    with open(os.path.join(data_dir, 'files-missing.txt'), 'w') as outfile:
        for item in items:
            if os.path.isfile(item.path):
                item.mtime = item.current_mtime()
                item.store()
            else:
                print(u"missing %s", item.path)
                # import pdb; pdb.set_trace()
                item.remove(False,True)
                tracks = Track.select().where(Track.path == item.path)
                for track in tracks:
                    album = track.album
                    artist = album.artist
                    genre = artist.genre
                    track.delete_instance()
                    if not album.track_set:
                        album.delete_instance()
                    if not artist.albums:
                        artist.delete_instance()
                    if not genre.artists:
                        genre.delete_instance()
                outfile.write(item.path + '\n')

def scan(config):
    _initialize(config)
    # import pdb; pdb.set_trace()
    from beets import dbcore
    id_sort = dbcore.query.FixedFieldSort(u"id", True)
    for bdb_album in bdb.albums(sort = id_sort):
        try:
            print("%s - %s" % (bdb_album.id, bdb_album.album.encode('utf-8')))
        except:
            pass
            #import pdb; pdb.set_trace()
        album, created = Album.get_or_create(beets_id=bdb_album.id)
        _sync_beets_album(album, bdb_album)
        for item in bdb_album.items():
            track, created = Track.get_or_create(beets_id=item.id)
            _sync_beets_item(track, item)
    for item in bdb.items(u'singleton:true'):
        track, created = Track.get_or_create(beets_id=item.id)
        _sync_beets_item(track, item)

def _find_children(genre, children):
    logger.info("called with {0}".format(genre.name))
    childs = [c for c in Genre.select().where(Genre.parent == genre.id)]
    children += childs
    for child in childs:
        _find_children(child, children)
    return children

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
    beets_id = IntegerField(null=True)
    catalognum = CharField(null=True)  # varchar
    comp = IntegerField(null=True)
    day = IntegerField(null=True)
    disctotal = IntegerField(null=True)
    genre = ForeignKeyField(Genre, related_name='albums', db_column='genre_id', null=True)
    label = ForeignKeyField(Label, related_name='albums', db_column='label_id', null=True)
    language = CharField(null=True)  # varchar
    mb_albumid = CharField(null=True)  # varchar
    # mb_albumartistid
    mb_releasegroupid = CharField(null=True)  # varchar
    month = IntegerField(null=True)
    name = CharField(null=True)  # varchar
    tracktotal = IntegerField(null=True)
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
    beets_id = IntegerField(null=True)
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
    # mb_artistid = CharField(null=True)
    # mb_albumartistid = CharField(null=True)
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
    updated_at = DateTimeField(null=True)
    created_at = DateTimeField(null=True)
    class Meta:
        db_table = 'tracks'
