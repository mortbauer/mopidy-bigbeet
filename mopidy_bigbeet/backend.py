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
        self.use_original_release_date = True
        logger.debug("Got library %s" % (self.db_path))
        self.playback = BigeetPlaybackProvider(audio=audio, backend=self)
        self.library = BigbeetLibraryProvider(backend=self)
        self.playlists = None
        self.uri_schemes = ['bigbeet']

    def _extract_uri(self, uri):
        logger.info("convert uri = %s" % uri.encode('ascii', 'ignore'))
        if not uri.startswith('bigbeet:'):
            raise ValueError('Invalid URI.')
        return uri.split(b':', 3)[1:4]

class BigeetPlaybackProvider(backend.PlaybackProvider):

    def translate_uri(self, uri):
        # import pdb; pdb.set_trace()
        logger.debug('translate_uri called %s', uri)
        local_uri = 'file://%s' % self.backend._extract_uri(uri)[2]
        logger.debug('local_uri: %s' % local_uri)
        return local_uri
