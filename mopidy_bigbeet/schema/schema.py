from __future__ import unicode_literals
import os.path
from peewee import *
from mopidy_bigbeet import Extension
from mopidy_bigbeet.schema import beet_schema, genre_schema

database = None
user_version = 1

def setup_db():
	import pdb; pdb.set_trace()
	database.create_tables([Genre])

def connect_db(db_path):
	global database
	database = SqliteDatabase(db_path, pragmas=(
        ('journal_mode', 'WAL'),
        ('user_version', user_version)
    ))
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
        bdb = beet_schema.BeetsLibrary(config['bigbeet']['beetslibrary']).lib
        albums = bdb.albums()
        genre = albums[0]['genre']
        gdb = genre_schema.GenreTree(data_dir)
        import pdb; pdb.set_trace()
	check_db(config)
	pass


class Genre(Model):
    name = CharField()
    class Meta:
        database = database

