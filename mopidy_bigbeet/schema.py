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


