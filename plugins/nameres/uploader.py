import pathlib
from typing import Union

import biothings, config
from biothings.hub.dataload.uploader import ParallelizedSourceUploader
from biothings.utils.storage import MergerStorage

from .parse import load_data_file
from .static import SYNONYM_FILE_COLLECTION, SYNONYM_BIG_FILE_COLLECTION, BASE_URL


biothings.config_for_app(config)


class NameResUploader(ParallelizedSourceUploader):
    name = "nameres"
    storage_class = MergerStorage
    __metadata__ = {"src_meta": {"url": BASE_URL}}

    def jobs(self) -> list[tuple]:
        file_names = [*SYNONYM_FILE_COLLECTION, *SYNONYM_BIG_FILE_COLLECTION.keys()]
        files = [pathlib.Path(self.data_folder).joinpath(file) for file in file_names]
        return [(f,) for f in files]

    def load_data(self, data_path: Union[str, pathlib.Path]):
        self.logger.info("Processing data from %s", data_path)
        return load_data_file(data_path)

    @classmethod
    def get_mapping(cls) -> dict:
        mapping = {
            "curie": {"type": "keyword"},
            "names": {"type": "text"},
            "types": {"types": "keyword"},
            "preferred_name": {"type": "text"},
            "shortest_name_length": {"types": "integer"},
            "clique_identifier_count": {"types": "integer"},
            "taxa": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
        }
        return mapping
