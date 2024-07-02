import pathlib
import urllib
from pathlib import Path
import re
import urllib
import urllib.request

import bs4

import biothings
from biothings import config


logger = config.logger


class ATCDumper(biothings.hub.dataload.dumper.LastModifiedHTTPDumper):
    SRC_NAME = "atc"
    SRC_URLS = ["https://raw.githubusercontent.com/fabkury/atcd/master/WHO%20ATC-DDD%202021-12-03.csv"]
    SRC_ROOT_FOLDER = Path(config.DATA_ARCHIVE_ROOT) / SRC_NAME
    SCHEDULE = None
    UNCOMPRESS = False

    def __init__(self):
        self.SRC_ROOT_FOLDER = pathlib.Path(self.SRC_ROOT_FOLDER).resolve().absolute()
        super().__init__(
            src_name=self.SRC_NAME,
            src_root_folder=self.SRC_ROOT_FOLDER,
            log_folder=config.LOG_FOLDER,
            archive=self.ARCHIVE,
        )

    def get_release(self) -> str:
        """
        Parses the data string from the CSV file itself

        Example:
        ['https://raw.githubusercontent.com/fabkury/atcd/master/WHO%20ATC-DDD%202021-12-03.csv']
        <202021-12-03>
        """
        src_url = self.SRC_URLS[0]
        parsed_url = urllib.parse.urlparse(src_url)
        url_path = pathlib.Path(parsed_url.path)
        release_version = url_path.stem.split("%")[-1]
        return release_version
