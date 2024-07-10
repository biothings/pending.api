"""
Uploader for the openFDA Drug Adverse Events data plugin

Handles the parsing of the document generated post_dump
from the dumper class instance
"""

import glob
import json
import os
import urllib.request
from datetime import datetime
from zipfile import ZipFile

import biothings.hub
import biothings.hub.dataload.storage
import biothings.hub.dataload.uploader
import yaml
from biothings import config
from biothings.utils.dataload import dict_convert, dict_sweep, dict_traverse

logger = config.logger


class OpenFDADrugUploader(biothings.hub.dataload.uploader.BaseSourceUploader):
    name = "openfda_drug_events"
    RECORD_SCHEMA_URL = "https://open.fda.gov/fields/drugevent.yaml"
    __metadata__ = {
        "src_meta": {
            "license_url": "https://open.fda.gov/license/",
            "licence": "CC0 1.0",
            "url": "https://open.fda.gov/",
        }
    }
    storage_class = biothings.hub.dataload.storage.RootKeyMergerStorage

    def __init__(self, db_conn_info, collection_name=None, log_folder=None, *args, **kwargs):
        # NOTE: using hardcoded URL for record schema
        with urllib.request.urlopen(self.RECORD_SCHEMA_URL) as response:
            schema = yaml.safe_load(response.read().decode("utf-8"))
        self.int_fields, self.categorical_fields = OpenFDADrugUploader._parse_schema(schema)
        super().__init__(db_conn_info, collection_name, log_folder, *args, **kwargs)

    def load_data(self, data_folder: str):
        process_key = lambda key: key.replace(" ", "_").lower()

        for file_path in glob.glob(os.path.join(data_folder, "*.json.zip")):
            with ZipFile(file_path) as zf:
                with zf.open(zf.namelist()[0]) as json_fd:
                    records = json.load(json_fd)["results"]
                    for record in records:
                        record = dict_sweep(record, vals=["", None], remove_invalid_list=True)
                        OpenFDADrugUploader._remove_dateformat_fields(record)
                        dict_traverse(record, self._process_field_vals, traverse_list=True)

                        record = dict_convert(record, process_key)
                        if "duplicate" in record.keys():
                            record["duplicate"] = record["duplicate"] == 1
                        record["_id"] = record["safetyreportid"]

                        yield record

    def _process_field_vals(self, k, v):
        """process dates, integers and categorical values"""
        new_val = v
        if k.endswith("date"):
            if len(v) == 8:
                new_val = datetime.strptime(v, "%Y%m%d").strftime("%Y-%m-%d")
            elif len(v) == 6:
                new_val = datetime.strptime(v, "%Y%m").strftime("%Y-%m")
            elif len(v) == 4:
                new_val = datetime.strptime(v, "%Y").strftime("%Y")
        elif k in self.int_fields:
            new_val = int(v)
        elif k in self.categorical_fields.keys() and v in self.categorical_fields[k].keys():
            new_val = self.categorical_fields[k][v]
        return k, new_val

    @staticmethod
    def _remove_dateformat_fields(data):
        if isinstance(data, dict):
            keys_to_remove = [key for key in data if key.endswith("dateformat")]
            for key in keys_to_remove:
                del data[key]
            for key, value in data.items():
                OpenFDADrugUploader._remove_dateformat_fields(value)
        elif isinstance(data, list):
            for item in data:
                OpenFDADrugUploader._remove_dateformat_fields(item)

    @staticmethod
    def _parse_schema(schema):
        """
        get categorical mappings and a set of int fields.
        NOTE: some int fields are categorical too, hence we take set
        difference while returning
        """
        int_fields = set()
        categorical_fields = {}

        def recursive_parser(data):
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, dict):
                        if isinstance(v.get("possible_values"), dict):
                            if v["possible_values"].get("type") == "one_of":
                                categorical_fields[k] = v["possible_values"]["value"]
                        if "int" in str(v.get("format")):
                            int_fields.add(k)  # str() to diffuse format being null
                        recursive_parser(v)
                    elif isinstance(v, list):
                        for list_val in v:
                            recursive_parser(list_val)

        recursive_parser(schema)
        int_fields.remove("drugintervaldosageunitnumb")  # mixed with floats
        int_fields.remove("drugseparatedosagenumb")  # mixed with floats
        return int_fields.difference(categorical_fields.keys()), categorical_fields
