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

    # @classmethod
    # def get_mapping(cls) -> dict:
    #     mapping = {
    #         "type": {"type": "keyword"},
    #         "ic": {"type": "keyword"},
    #         "identifiers": {
    #             "type": "nested",
    #             "properties": {
    #                 "i": {"type": "keyword"},
    #                 "l": {"type": "keyword"},
    #                 "d": {"type": "string"},
    #                 "t": {"type": "string"},
    #             },
    #         },
    #         "preferred_name": {"type": "string"},
    #         "taxa": {"type": "string"},
    #     }
    #     return mapping
