import logging

from mopidy import backend
from mopidy_bigbeet import Extension
import pykka
import os.path
from .library import BigbeetLibraryProvider

logger = logging.getLogger(__name__)

class BigbeetBackend(pykka.ThreadingActor, backend.Backend):

    def __init__(self, config, audio):
        super(BigbeetBackend, self).__init__()
        data_dir = Extension.get_data_dir(config)
        self.db_path = os.path.join(data_dir, b'library.db')
        logger.debug("Got library %s" % (self.db_path))
        self.playback = BigeetPlaybackProvider(audio=audio, backend=self)
        self.library = BigbeetLibraryProvider(backend=self)
        self.playlists = None
        self.uri_schemes = ['bigbeet']

    def _extract_uri(self, uri):
        logger.debug("convert uri = %s" % uri.encode('ascii', 'ignore'))
        if not uri.startswith('bigbeet:'):
            raise ValueError('Invalid URI.')
        path = uri.split(b':', 3)[3]
        beets_id = uri.split(b':', 3)[2]
        item_type = uri.split(b':', 3)[1]
        logger.debug("extracted path = %s id = %s type = %s" % (
            path.encode('ascii', 'ignore'), beets_id, item_type))
        return {'path': path,
                'beets_id': int(beets_id),
                'item_type': item_type}

class BigeetPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        logger.debug('translate_uri called %s', uri)
        local_uri = 'file://%s' % self.backend._extract_uri(uri)['path']
        logger.debug('local_uri: %s' % local_uri)
        return local_uri
