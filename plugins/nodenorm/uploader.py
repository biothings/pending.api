import pathlib

import biothings, config
from biothings.hub.dataload.uploader import ParallelizedSourceUploader
from biothings.utils.storage import MergerStorage

from .parse import load_data_file


biothings.config_for_app(config)


class NodeNormUploader(ParallelizedSourceUploader):
    name = "nodenorm"
    storage_class = MergerStorage
    __metadata__ = {
        "src_meta": {
            "url": "https://stars.renci.org/var/babel_outputs/2025jan23/compendia",
        }
    }

    def jobs(self):
        data_path = pathlib.Path(self.data_folder).glob("**/*")
        files = [file for file in data_path if file.is_file()]
        return [(f,) for f in files]

    def load_data(self, data_path):
        self.logger.info("Processing data from %s", data_path)
        return load_data_file(data_path)

    @classmethod
    def get_mapping(cls) -> dict:
        mapping = {
            "type": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
            "ic": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
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
                    "t": {"type": "text"},
                }
            },
            "preferred_name": {"type": "text"},
            "taxa": {"type": "text"},
            "all": {"type": "text"},
        }
        return mapping
