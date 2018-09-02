from beets.plugins import BeetsPlugin
from subprocess import call

class BigbeetPlugin(BeetsPlugin):
    def __init__(self):
        super(BigbeetPlugin, self).__init__()
        self.register_listener('database_change', self.db_changed)
        self.changed_albums = {}
        self.changed_items = {}

    def db_changed(self, lib, model):
        if model.__class__.__name__ == 'Item':
            self.changed_items[model.id] = model
        elif model.__class__.__name__ == 'Album':
            self.changed_albums[model.id] = model
        else:
            print('Unknown Model {1}'.format(model.__class__.__name__))
            import pdb; pdb.set_trace()
        self.register_listener('cli_exit', self.update)

    def update(self, lib):
        for album_id, album in self.changed_albums.iteritems():
            try:
                print("Album changed with id: {0} with {1}".format(album_id, album.genre))
            except:
                import pdb;
                pdb.set_trace()
            call(['mopidy', 'bigbeet', 'beet_update', '-a', str(album_id)])
        for item_id, item in self.changed_items.iteritems():
            print("Item changed with id: {0} at {1}".format(item_id,item.path))
            call(['mopidy', 'bigbeet', 'beet_update', '-i', str(item_id)])
