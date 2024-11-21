"""
Pending.api specific application builder for overriding
the default builder provided by the biothings.api package

Responsible for generating the tornado.web.Application instance
"""

from biothings.web.applications import TornadoBiothingsAPI
from biothings.web.services.namespace import BiothingsNamespace
from biothings.web.settings.configs import ConfigPackage

from web.settings.configuration import PendingAPIConfigModule


class PendingAPI(TornadoBiothingsAPI):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def get_app(cls, config, settings=None, handlers=None):
        """
        Return the tornado.web.Application defined by this config.
        **Additional** settings and handlers are accepted as parameters.
        """
        if isinstance(config, PendingAPIConfigModule):
            biothings = BiothingsNamespace(config)
            _handlers = TornadoBiothingsAPI._get_handlers(biothings, handlers)
            _settings = TornadoBiothingsAPI._get_settings(biothings, settings)
            app = cls(_handlers, **_settings)
            app.biothings = biothings
            app._populate_optionsets(config, _handlers)
            app._populate_handlers(_handlers)
            return app
        if isinstance(config, ConfigPackage):
            biothings = BiothingsNamespace(config.root)
            _handlers = [(f"/{c.APP_PREFIX}/.*", cls.get_app(c, settings)) for c in config.modules]
            _settings = TornadoBiothingsAPI._get_settings(biothings, settings)
            app = cls(_handlers + handlers or [], **_settings)
            app.biothings = biothings
            # app._populate_optionsets(config, handlers or [])
            # app._populate_handlers(handlers or [])
            app._populate_optionsets(config, _handlers + handlers or [])
            app._populate_handlers(_handlers + handlers or [])
            return app
        raise TypeError("Invalid config type. Must be a ConfigModule or ConfigPackage.")
