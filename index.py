"""
Production Sites:
https://pending.biothings.io/
https://pending.ci.biothings.io/
https://pending.test.biothings.io/
https://biothings.ncats.io/
"""

import logging
import os
import sys
import pathlib

from tornado.options import define, options

from web.handlers import EXTRA_HANDLERS
from web.launcher import PendingAPILauncher

logger = logging.getLogger(__name__)


# Command Line Utilities
# --------------------------

define("port", default=8000, help="run on the given port")
define("debug", default=False, help="debug settings like logging preferences")
define("address", default=None, help="host address to listen to, default to all interfaces")
define("autoreload", default=False, help="auto reload the web server when file change detected")
define("conf", default="config", help="specify a config module name to import")
define("dir", default=os.getcwd(), help="path to app directory that includes config.py")


def main(app_handlers: list = None, app_settings: dict = None, use_curl: bool = False):
    """
    Entrypoint for the pending.api application launcher

    Ported from the biothings.web.launcher
    """
    if app_handlers is None:
        app_handlers = []

    if app_settings is None:
        app_handlers = {}

    options.parse_command_line()
    application_directory = pathlib.Path(options.dir).resolve().absolute()
    if application_directory not in sys.path:
        sys.path.append(str(application_directory))

    launcher = PendingAPILauncher(options.conf)

    try:
        if app_settings:
            launcher.settings.update(app_settings)
        if app_handlers:
            launcher.handlers = app_handlers
        if use_curl:
            launcher.enable_curl_httpclient()

        launcher.host = options.address
        launcher.settings.update(debug=options.debug)
        launcher.settings.update(autoreload=options.autoreload)
    except Exception as gen_exc:
        logger.exception(gen_exc)
        logger.error("Unable to start the pending.api launcher")
        raise gen_exc

    launcher.start(host=launcher.host, port=options.port)


if __name__ == "__main__":
    pending_handlers = EXTRA_HANDLERS
    pending_settings = {"static_path": "static"}
    main(
        app_handlers=pending_handlers,
        app_settings=pending_settings,
        use_curl=False,
    )
