from __future__ import unicode_literals

import logging
import os

from mopidy import config, ext
from mopidy import commands


__version__ = '0.0.1'

logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = 'Mopidy-Bigbeet'
    ext_name = 'bigbeet'
    version = __version__


    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(Extension, self).get_config_schema()
        schema['beetslibrary'] = config.String()
        schema['bb_library'] = config.String()
        return schema

    def get_command(self):
        from .commands import BigbeetCommand
        return BigbeetCommand()


    def setup(self, registry):
        from .backend import BigbeetBackend
        registry.add('backend', BigbeetBackend)
        pass
