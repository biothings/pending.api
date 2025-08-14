import pathlib
from typing import Union

import biothings, config
from biothings.hub.dataload.uploader import ParallelizedSourceUploader
from biothings.utils.storage import MergerStorage

from .parse import load_data_file
from .dumper import NODENORM_FILE_COLLECTION, NODENORM_BIG_FILE_COLLECTION, BASE_URL, CONFLATION_LOOKUP_DATABASE


biothings.config_for_app(config)


class NodeNormUploader(ParallelizedSourceUploader):
    name = "nodenorm"
    storage_class = MergerStorage
    __metadata__ = {"src_meta": {"url": BASE_URL}}

    def jobs(self) -> list[tuple]:
        file_names = [*NODENORM_FILE_COLLECTION, *NODENORM_BIG_FILE_COLLECTION.keys()]
        files = [pathlib.Path(self.data_folder).joinpath(file) for file in file_names]
        conflation_database = pathlib.Path(self.data_folder).joinpath(CONFLATION_LOOKUP_DATABASE)
        return [(f, conflation_database) for f in files]

    def load_data(self, data_path: Union[str, pathlib.Path], conflation_database: Union[str, pathlib.Path]):
        self.logger.info("Processing data from %s", data_path)
        return load_data_file(data_path, conflation_database)

    @classmethod
    def get_mapping(cls) -> dict:
        mapping = {
            "type": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
            "ic": {"type": "float"},
            "identifiers": {
                "properties": {
                    "i": {
                        "type": "keyword",
                        "normalizer": "keyword_lowercase_normalizer",
                        "copy_to": "all",  # default field
                    },
                    "l": {
                        "type": "text",
                        "fields": {"raw": {"type": "keyword", "ignore_above": 512}},
                        "copy_to": "all",  # default field
                    },
                    "d": {"type": "text"},
                    "t": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                    "c": {"properties": {"gp": {"type": "keyword"}, "cd": {"type": "keyword"}}},
                }
            },
            "preferred_name": {"type": "text"},
            "taxa": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
            "all": {"type": "text"},
        }
        return mapping
