"""
Uploader for the FDA Drugs data plugin

Handles the parsing of the document generated post_dump
from the dumper class instance
"""

from pathlib import Path
from typing import Union

import biothings.hub
import biothings.hub.dataload.uploader

from biothings import config


class FDA_DrugUploader(biothings.hub.dataload.uploader.BaseSourceUploader):
    name = "fda_drugs"
    __metadata__ = {
        "src_meta": {
            "url": "https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files",
            "license_url": None,
        }
    }

    def load_data(self, data_folder: Union[str, Path]):
        """
        Loads the structured FDA drugs data
        """
        structured_fda_drug_data = Path(data_folder).joinpath("FDA_DRUGS_GROUPING.txt")
        with open(structured_fda_drug_data, "r", encoding="utf-8") as file_handle:
            for raw_entry in file_handle.readlines():
                structured_entry = raw_entry.strip().split("\t")
                document = {
                    "drug_name": structured_entry[0],
                    "active_ingredients": structured_entry[1],
                    "strength": structured_entry[2],
                    "dosage_form": structured_entry[3],
                    "marketing_status": structured_entry[4],
                    "te_code": structured_entry[5],
                    "reference_standard": structured_entry[6],
                }
                yield document

    @classmethod
    def get_mapping(self) -> dict:
        """
        Elasticsearch mapping for representing the structured FDA drugs data
        Entry Structure:
        {
            <Drug Name>
            <Active Ingredients>
            <Strength>
            <Dosage Form/Route>
            <Marketing Status>
            <TE Code>
            <RLD>
            <RS>
        }
        """
        elasticsearch_mapping = {
            "associatedWith": {
                "properties": {
                    "drug_name": {"type": "keyword_lowercase_normalizer"},
                    "active_ingredients": {"type": "keyword_lowercase_normalizer"},
                    "strength": {"type": "keyword_lowercase_normalizer"},
                    "dosage_form": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
                    "marketing_status": {"type": "keyword", "normalizer": "keyword"},
                    "te_code": {"type": "keyword", "normalizer": "keyword"},
                    "rld": {"type": "keyword", "normalizer": "keyword"},
                    "reference_standard": {"type": "keyword", "normalizer": "keyword"},
                },
            }
        }
        return elasticsearch_mapping
