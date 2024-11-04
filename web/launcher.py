"""
Biothings API Launcher

In this module, we have three framework-specific launchers
and a command-line utility to provide both programmatic and
command-line access to start Biothings APIs.
"""

import logging
from pprint import pformat

import tornado.httpserver
import tornado.ioloop
import tornado.log
import tornado.web

from biothings import __version__
from biothings.web.applications import BiothingsAPI
from biothings.web.launcher import TornadoAPILauncher
from biothings.web.settings.configs import ConfigPackage

from web.settings.configuration import load_configuration, PendingAPIConfigModule

logger = logging.getLogger(__name__)


class PendingAPILauncher:
    """
    Specific launcher to the pending.api. Designed
    specifically for handling the volume of plugins
    """

    def __init__(self, config: str = None):
        logging.info("Biothings API %s", __version__)
        self.settings = {"debug": False}
        self.handlers = []
        self.config = load_configuration(config)
        self.application = BiothingsAPI.get_app(self.config, self.settings, self.handlers)
        self._configure_logging()

    def _configure_logging(self):
        root_logger = logging.getLogger()

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
