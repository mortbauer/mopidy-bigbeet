from __future__ import unicode_literals
from playhouse.migrate import *

#my_db = SqliteDatabase('my_database.db')
#migrator = SqliteMigrator(my_db)

#title_field = CharField(default='')
#status_field = IntegerField(null=True)

#migrate(
#    migrator.add_column('some_table', 'title', title_field),
#    migrator.add_column('some_table', 'status', status_field),
#    migrator.drop_column('some_table', 'old_column'),
#)
class Migration20160913():

    def __init__(self, my_db):
        migrator = SqliteMigrator(my_db)
        pass
