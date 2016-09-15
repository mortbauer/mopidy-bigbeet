from beets.plugins import BeetsPlugin
from subprocess import call

class BigbeetPlugin(BeetsPlugin):
    def __init__(self):
        super(BigbeetPlugin, self).__init__()
        self.register_listener('database_change', self.db_changed)
        self.changed_albums = []
        self.changed_items = []

    def db_changed(self, lib, model):
        if model.__class__.__name__ == 'Item':
            self.changed_items.append(model.id)
        elif model.__class__.__name__ == 'Album': 
            self.changed_albums.append(model.id)
        else:
            print "Unknown Model {}".format(model.__class__.__name__)
            import pdb; pdb.set_trace()
        self.register_listener('cli_exit', self.update)

    def update(self, lib):
        for item_id in set(self.changed_items):
            print "Item changed with id: {0}".format(item_id)
            call(['mopidy', 'bigbeet', 'beet_update', '-i', str(item_id)])
        for album_id in set(self.changed_albums):
            print "Album changed with id: {0}".format(album_id)
            call(['mopidy', 'bigbeet', 'beet_update', '-a', str(album_id)])
