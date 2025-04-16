"""
Uploader for the ebi_gene2phenotype data plugin
"""

from pathlib import Path
from typing import Union

import biothings
from biothings import config
import biothings.hub.dataload.uploader

from .mapping import ebi_gene2pheno_mapping
from .parser import upload_documents


logger = config.logger


class EBI2PhenotypeUploader(biothings.hub.dataload.uploader.IgnoreDuplicatedSourceUploader):
    name = "ebi_gene2phenotype"
    src_meta = {
        "url": "https://ftp.ebi.ac.uk/pub/databases/gene2phenotype/",
        "license_url": "https://www.ebi.ac.uk/about/terms-of-use/#general",
        "description": "Search entities & relations in 35+ million biomedical publications.",
    }

    def load_data(self, data_path: Union[str, Path]):
        yield from upload_documents(data_path)

    @classmethod
    def get_mapping(self) -> dict:
        return ebi_gene2pheno_mapping(self)
