from __future__ import unicode_literals
import os.path
from peewee import *
from . import Extension

database = None
user_version = 1
C14N_TREE = os.path.join(os.path.dirname(__file__), 'genres-tree.yaml')

def setup_db():
	import pdb; pdb.set_trace()
	database.create_tables([Genre])

def connect_db(db_path)
	global database
	database = SqliteDatabase(db_path, pragmas=(
        ('journal_mode', 'WAL'),
        ('user_version', user_version)
    ))
	database.connect()

def migrate_db()
    print "This needs to be build"
	
def check_db(config):
	data_dir = Extension.get_data_dir(config)
	db_path = os.path.join(data_dir, b'library.db')
	db_existed = os.path.isfile(db_path)
    connect_db(db_path)
	if not db_existed:
		setup_db()
	elif dict(database._pragmas)['user_version'] != user_version
		migrate_db()

def scan(config):
	check_db(config)
	pass


class Genre(Model):
    name = CharField()
    class Meta:
        database = database


 def flatten_tree(elem, path, branches):
    """Flatten nested lists/dictionaries into lists of strings
    (branches).
    """
    if not path:
        path = []

    if isinstance(elem, dict):
        for (k, v) in elem.items():
            flatten_tree(v, path + [k], branches)
    elif isinstance(elem, list):
        for sub in elem:
            flatten_tree(sub, path, branches)
    else:
        branches.append(path + [unicode(elem)])


def find_parents(candidate, branches):
    """Find parents genre of a given genre, ordered from the closest to
    the further parent.
    """
    for branch in branches:
        try:
            idx = branch.index(candidate.lower())
            return branch[:idx + 1][::-1]
        except ValueError:
            continue
    return [candidate]



database = SqliteDatabase('/data/music/music_var/beetslibrary.blb', **{})

class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = database

class AlbumAttributes(BaseModel):
    entity = IntegerField(db_column='entity_id', index=True, null=True)
    key = TextField(null=True)
    value = TextField(null=True)

    class Meta:
        db_table = 'album_attributes'
        indexes = (
            (('entity', 'key'), True),
        )

class Albums(BaseModel):
    added = FloatField(null=True)
    album = TextField(null=True)
    albumartist = TextField(null=True)
    albumartist_credit = TextField(null=True)
    albumartist_sort = TextField(null=True)
    albumdisambig = TextField(null=True)
    albumstatus = TextField(null=True)
    albumtype = TextField(null=True)
    artpath = BlobField(null=True)
    asin = TextField(null=True)
    catalognum = TextField(null=True)
    comp = IntegerField(null=True)
    country = TextField(null=True)
    day = IntegerField(null=True)
    disctotal = IntegerField(null=True)
    genre = TextField(null=True)
    label = TextField(null=True)
    language = TextField(null=True)
    mb_albumartistid = TextField(null=True)
    mb_albumid = TextField(null=True)
    mb_releasegroupid = TextField(null=True)
    month = IntegerField(null=True)
    original_day = IntegerField(null=True)
    original_month = IntegerField(null=True)
    original_year = IntegerField(null=True)
    rg_album_gain = FloatField(null=True)
    rg_album_peak = FloatField(null=True)
    script = TextField(null=True)
    tracktotal = IntegerField(null=True)
    year = IntegerField(null=True)

    class Meta:
        db_table = 'albums'

class ItemAttributes(BaseModel):
    entity = IntegerField(db_column='entity_id', index=True, null=True)
    key = TextField(null=True)
    value = TextField(null=True)

    class Meta:
        db_table = 'item_attributes'
        indexes = (
            (('entity', 'key'), True),
        )

class Items(BaseModel):
    acoustid_fingerprint = TextField(null=True)
    acoustid = TextField(db_column='acoustid_id', null=True)
    added = FloatField(null=True)
    album = TextField(null=True)
    album_id = IntegerField(null=True)
    albumartist = TextField(null=True)
    albumartist_credit = TextField(null=True)
    albumartist_sort = TextField(null=True)
    albumdisambig = TextField(null=True)
    albumstatus = TextField(null=True)
    albumtype = TextField(null=True)
    artist = TextField(null=True)
    artist_credit = TextField(null=True)
    artist_sort = TextField(null=True)
    asin = TextField(null=True)
    bitdepth = IntegerField(null=True)
    bitrate = IntegerField(null=True)
    bpm = IntegerField(null=True)
    catalognum = TextField(null=True)
    channels = IntegerField(null=True)
    comments = TextField(null=True)
    comp = IntegerField(null=True)
    composer = TextField(null=True)
    country = TextField(null=True)
    day = IntegerField(null=True)
    disc = IntegerField(null=True)
    disctitle = TextField(null=True)
    disctotal = IntegerField(null=True)
    encoder = TextField(null=True)
    format = TextField(null=True)
    genre = TextField(null=True)
    grouping = TextField(null=True)
    initial_key = TextField(null=True)
    label = TextField(null=True)
    language = TextField(null=True)
    length = FloatField(null=True)
    lyrics = TextField(null=True)
    mb_albumartistid = TextField(null=True)
    mb_albumid = TextField(null=True)
    mb_artistid = TextField(null=True)
    mb_releasegroupid = TextField(null=True)
    mb_trackid = TextField(null=True)
    media = TextField(null=True)
    month = IntegerField(null=True)
    mtime = FloatField(null=True)
    original_day = IntegerField(null=True)
    original_month = IntegerField(null=True)
    original_year = IntegerField(null=True)
    path = BlobField(null=True)
    rg_album_gain = FloatField(null=True)
    rg_album_peak = FloatField(null=True)
    rg_track_gain = FloatField(null=True)
    rg_track_peak = FloatField(null=True)
    samplerate = IntegerField(null=True)
    script = TextField(null=True)
    title = TextField(null=True)
    track = IntegerField(null=True)
    tracktotal = IntegerField(null=True)
    year = IntegerField(null=True)

    class Meta:
        db_table = 'items'

