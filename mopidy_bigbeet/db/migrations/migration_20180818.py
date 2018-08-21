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
            schema.UserTag.create_table()
            schema.TrackTag.create_table()
            migrate(self.migrator.add_column('artists', 'albumartist_initial',
                                             CharField(null=True))
                    )
            schema.SchemaMigration.create(version = '20180818' )

    def update_db(self):
        pass
