"""
Biothings API Launcher

In this module, we have three framework-specific launchers
and a command-line utility to provide both programmatic and
command-line access to start Biothings APIs.
"""

import logging
import pathlib
from pprint import pformat

import tornado.httpserver
import tornado.ioloop
import tornado.log
import tornado.options
import tornado.web
from swagger_ui import api_doc

from biothings import __version__
from biothings.web.settings.configs import ConfigPackage

from web.application import PendingAPI
from web.settings.configuration import load_configuration, PendingAPIConfigModule

logger = logging.getLogger(__name__)


class PendingAPILauncher:
    """
    Specific launcher to the pending.api. Designed
    specifically for handling the volume of plugins
    """

    def __init__(
        self, options: tornado.options.OptionParser, app_handlers: list[tuple], app_settings: dict, use_curl: bool
    ):
        logging.info("Biothings API %s", __version__)
        self.handlers = app_handlers
        self.host = options.address
        self.settings = self._configure_settings(options, app_settings)
        self.config = load_configuration(options.conf)
        self._configure_logging()

        self.application = PendingAPI.get_app(self.config, self.settings, self.handlers)
        self._configure_swagger(self.application)

        if use_curl:
            self.enable_curl_httpclient()

    def _configure_swagger(self, application: tornado.web.Application) -> None:
        """
        Muliple swagger UI endpoints now:
            * nodenorm
            * nameres

        nodenorm openapi file location: /web/handlers/nodenorm/specification/openapi.json
        nameres  openapi file location: /web/handlers/nameres/specification/openapi.json
        """
        web_directory = pathlib.Path(__file__).resolve().absolute().parent
        nodenorm_specification_directory = web_directory / "handlers" / "nodenorm" / "specification"
        nodenorm_spec = nodenorm_specification_directory.joinpath("openapi.json")
        api_doc(
            application, config_path=nodenorm_spec, url_prefix="/nodenorm/api/doc", title="Nodenorm API Documentation"
        )

        nameres_specification_directory = web_directory / "handlers" / "nameres" / "specification"
        nameres_spec = nameres_specification_directory.joinpath("openapi.json")
        api_doc(application, config_path=nameres_spec, url_prefix="/nameres/api/doc", title="Nameres API Documentation")

    def _configure_settings(self, options: tornado.options.OptionParser, app_settings: dict) -> dict:
        """
        Configure the `settings` attribute for the launcher
        """
        app_settings.update(debug=options.debug)
        app_settings.update(autoreload=options.autoreload)
        return app_settings

    def _configure_logging(self):
        root_logger = logging.getLogger()

        config = {}
        if isinstance(self.config, ConfigPackage):
            config = self.config.root
        elif isinstance(self.config, PendingAPIConfigModule):
            config = self.config

        if hasattr(config, "LOGGING_FORMAT"):
            for handler in root_logger.handlers:
                if isinstance(handler.formatter, tornado.log.LogFormatter):
                    handler.formatter._fmt = config.LOGGING_FORMAT

        logging.getLogger("urllib3").setLevel(logging.ERROR)
        logging.getLogger("elasticsearch").setLevel(logging.WARNING)

        if self.settings["debug"]:
            root_logger.setLevel(logging.DEBUG)
        else:
            root_logger.setLevel(logging.INFO)

    @staticmethod
    def enable_curl_httpclient():
        """
        Use curl implementation for tornado http clients.
        More on https://www.tornadoweb.org/en/stable/httpclient.html
        """
        curl_httpclient_option = "tornado.curl_httpclient.CurlAsyncHTTPClient"
        tornado.httpclient.AsyncHTTPClient.configure(curl_httpclient_option)

    def start(self, host: str = None, port: int = None):
        """
        Starts the HTTP server and IO loop used for running
        the pending.api backend
        """

        if host is None:
            host = "0.0.0.0"

        if port is None:
            port = 8000
        port = str(port)

        http_server = tornado.httpserver.HTTPServer(self.application, xheaders=True)
        http_server.listen(port, host)

        logger.info(
            "pending.api web server is running on %s:%s ...\n pending.api handlers:\n%s",
            host,
            port,
            pformat(self.application.biothings.handlers, width=200),
        )
        loop = tornado.ioloop.IOLoop.instance()
        loop.start()
