from __future__ import unicode_literals
from peewee import *


database = SqliteDatabase(None)
user_version = 1


class BigbeetSchema():

    def __init__(self, db_path):
        database.init(db_path,
                      pragmas=(
                               ('journal_mode', 'WAL'),
                               ('user_version', user_version)
                               ))
        self.database = database

    def setup_db(self):
        # import pdb; pdb.set_trace()
        database.drop_tables([self.Genre,
                              self.AlbumGroup,
                              self.Album,
                              self.ArtistSecondaryGenre,
                              self.Artist,
                              self.Label,
                              self.SecondaryGenre,
                              self.Track])
        database.create_tables([self.Genre,
                                self.AlbumGroup,
                                self.Album,
                                self.ArtistSecondaryGenre,
                                self.Artist,
                                self.Label,
                                self.SecondaryGenre,
                                self.Track])

