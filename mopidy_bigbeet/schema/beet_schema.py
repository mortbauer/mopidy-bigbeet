from __future__ import unicode_literals
import logging
import os.path
from mopidy.exceptions import ExtensionError
logger = logging.getLogger(__name__)
#database = SqliteDatabase('/data/music/music_var/beetslibrary.blb', **{})

class BeetsLibrary():
    
    def __init__(self,db_path):
        try:
            import beets.library
        except:
            logger.error('BeetsLibrary: could not import beets library')
        if not os.path.isfile(db_path):
            raise ExtensionError('Can not find %s'
                                 % (db_path))
        try:
            self.lib = beets.library.Library(db_path)
        except sqlite3.OperationalError, e:
            logger.error('BeetsLibrary: %s', e)
            raise ExtensionError('Mopidy-Bigbeet can not open %s',
                                 db_path)
        except sqlite3.DatabaseError, e:
            logger.error('BeetsLibrary: %s', e)
            raise ExtensionError('Mopidy-Bigbeet can not open %s',
                                 db_path)
        except:
            print "Unexpected error:", sys.exc_info()[0]
            pass
        print db_path
