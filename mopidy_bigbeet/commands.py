from __future__ import absolute_import, print_function, unicode_literals

from mopidy import commands, exceptions
# from . import Extension
from mopidy_bigbeet.schema import schema


class BigbeetCommand(commands.Command):

    """Command parser and runner for building trees of commands.
    This class provides a wraper around :class:`argparse.ArgumentParser`
    for handling this type of command line application in a better way than
    argprases own sub-parser handling.
    """

    def __init__(self):
        super(BigbeetCommand, self).__init__()
        self.set(base_verbosity_level=-1)
        # self.add_argument('--foo')
        self.add_child('scan',ScanCommand())
        self.add_child('check_genres',CheckGenres())
        self.add_child('update',UpdateCommand())
        self.add_child('beet_update',BeetUpdateCommand())

class CheckGenres(commands.Command):
    help = 'Check for genres missing in genres_tree file.'

    def _init__(self):
        super(ScanCommand, self).__init__()
        self.set(base_verbosity_level=-1)

    def run(self, args, config):
        res = schema.check_genres(config)
        return 0

class ScanCommand(commands.Command):
    help = 'Scan beets library and populate the local library'

    def __init__(self):
        super(ScanCommand, self).__init__()
        self.set(base_verbosity_level=-1)

    def run(self, args, config):
        # import pdb; pdb.set_trace()
        res = schema.scan(config)
        # db.load(Extension.get_data_dir(config))
    	return 0

class UpdateCommand(commands.Command):
    help = 'Update the local library'

    def __init__(self):
        super(UpdateCommand, self).__init__()
        self.set(base_verbosity_level=-1)
        self.add_argument('--limit',
                          action='store', type=int, dest='limit', default=None,
                          help='Maxmimum number of tracks to scan')

    def run(self, args, config):
        # import pdb; pdb.set_trace()
        res = schema.update(config)
        # db.load(Extension.get_data_dir(config))
    	return 0

class BeetUpdateCommand(commands.Command):
    help = 'Update the local library via bigbeetplugin'

    def __init__(self):
        super(BeetUpdateCommand, self).__init__()
        self.set(base_verbosity_level=-1)
        self.add_argument('-i','--item',
                          action='store', type=int, dest='item_id', default=None,
                          help='beet item id to update')
        self.add_argument('-a','--album',
                          action='store', type=int, dest='album_id', default=None,
                          help='beet album id to update')

    def run(self, args, config):
        if args.item_id:
            schema.item_update(config,args.item_id)
        if args.album_id:
            schema.album_update(config,args.album_id)
    	return 0
