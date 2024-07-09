"""
Methods for pulling down the openFDA Drug Adverse Events data
"""

import json
import random
import urllib.request
from pathlib import Path
from typing import List

import biothings.hub
from biothings import config

logger = config.logger


class OpenFDADrugEventsDumper(biothings.hub.dataload.dumper.LastModifiedHTTPDumper):
    DIR_STRUCTURE_URL = "https://api.fda.gov/download.json"
    SRC_NAME = "openfda_drug_events"
    SRC_ROOT_FOLDER = Path(config.DATA_ARCHIVE_ROOT) / SRC_NAME
    SCHEDULE = None
    UNCOMPRESS = False
    SRC_URLS = []

    def __init__(self):
        self.SRC_URLS = OpenFDADrugEventsDumper.extract_download_urls()
        self.__class__.SRC_URLS = self.SRC_URLS

        super().__init__()

    @classmethod
    def extract_download_urls(cls) -> List[str]:
        with urllib.request.urlopen(cls.DIR_STRUCTURE_URL) as response:
            source_meta = json.loads(response.read().decode("utf-8"))
            source_urls = tuple(rec["file"] for rec in source_meta["results"]["drug"]["event"]["partitions"])

        return random.sample(source_urls, k=int(config.sample_frac * len(source_urls)))
