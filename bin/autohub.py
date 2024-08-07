#!/usr/bin/env python

import sys, os, logging

# shut some mouths...
import botocore

logging.getLogger("elasticsearch").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)
logging.getLogger("tornado").setLevel(logging.ERROR)
logging.getLogger("botocore").setLevel(logging.ERROR)

import config, biothings
from biothings.utils.version import set_versions
from standalone.utils.version import set_standalone_version

# fill app & autohub versions
set_versions(config, ".")
set_standalone_version(config, "standalone")
biothings.config_for_app(config)
# now use biothings' config wrapper
config = biothings.config
logging.info("Hub DB backend: %s" % config.HUB_DB_BACKEND)
logging.info("Hub database: %s" % config.DATA_HUB_DB_DATABASE)

from standalone.hub import DynamicIndexerFactory
from hub import PendingHubServer

server = PendingHubServer(
    config.VERSION_URLS,
    indexer_factory=DynamicIndexerFactory(config.VERSION_URLS, config.ES_HOST, suffix=""),
    source_list=None,
    name="Pending API Hub (frontend)",
    api_config=None,
    dataupload_config=False,
    websocket_config=False,
)


if __name__ == "__main__":
    server.start()
