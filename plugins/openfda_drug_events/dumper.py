"""
Methods for pulling down the openFDA Drug Adverse Events data
"""

import json
import os
import random
import urllib.request
from pathlib import Path
from typing import List

import biothings.hub
from biothings import config

logger = config.logger


class OpenFDADrugEventsDumper(biothings.hub.dataload.dumper.LastModifiedHTTPDumper):
    DIR_STRUCTURE_URL = "https://api.fda.gov/download.json"
    SAMPLE_FRAC = 1.0
    SRC_NAME = "openfda_drug_events"
    SRC_ROOT_FOLDER = Path(config.DATA_ARCHIVE_ROOT) / SRC_NAME
    SCHEDULE = None
    UNCOMPRESS = False
    SRC_URLS = []

    def __init__(self):
        self.SRC_URLS = OpenFDADrugEventsDumper.extract_download_urls()
        self.__class__.SRC_URLS = self.SRC_URLS

        super().__init__()

    def create_todump_list(self, force=False):
        assert type(self.__class__.SRC_URLS) is list, "SRC_URLS should be a list"
        assert self.__class__.SRC_URLS, "SRC_URLS list is empty"
        self.set_release()  # so we can generate new_data_folder
        for src_url in self.__class__.SRC_URLS:
            # add year and quarter to filename to prevent overwriting
            prefix, filename = os.path.split(src_url)
            filename = os.path.basename(prefix) + "_" + filename
            new_localfile = os.path.join(self.new_data_folder, filename)
            try:
                current_localfile = os.path.join(self.current_data_folder, filename)
            except TypeError:
                # current data folder doesn't even exist
                current_localfile = new_localfile

            remote_better = self.remote_is_better(src_url, current_localfile)
            if force or current_localfile is None or remote_better:
                new_localfile = os.path.join(self.new_data_folder, filename)
                self.to_dump.append({"remote": src_url, "local": new_localfile})

    @classmethod
    def extract_download_urls(cls) -> List[str]:
        with urllib.request.urlopen(cls.DIR_STRUCTURE_URL) as response:
            source_meta = json.loads(response.read().decode("utf-8"))
            source_urls = tuple(rec["file"] for rec in source_meta["results"]["drug"]["event"]["partitions"])

        return random.sample(source_urls, k=int(cls.SAMPLE_FRAC * len(source_urls)))
