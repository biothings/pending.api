"""
Uploader for the FDA Drugs data plugin

Handles the parsing of the document generated post_dump
from the dumper class instance
"""

from pathlib import Path
from typing import Union

import biothings.hub
import biothings.hub.dataload.uploader


class FDA_DrugUploader(biothings.hub.dataload.uploader.BaseSourceUploader):
    name = "fda_drugs"
    __metadata__ = {
        "src_meta": {
            "url": "https://www.fda.gov/drugsatfda",
            "license": "CC0 1.0 Universal",
            "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
            "description": "Drugs@FDA includes information about drugs, including biological products, approved for human use in the United States (see (https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=faq.page)), but does not include information about FDA-approved products regulated by the Center for Biologics Evaluation and Research (for example, vaccines, allergenic products, blood and blood products, plasma derivatives, cellular and gene therapy products).",
        }
    }

    def load_data(self, data_folder: Union[str, Path]):
        """
        Loads the structured FDA drugs data. After the post dump merging of the various data
        sources provided by the FDA, we simply have to extract the merged documents rows into
        a JSON document
        """
        structured_fda_drug_data = Path(data_folder).joinpath("FDA_DRUGS_GROUPING.txt")
        with open(structured_fda_drug_data, "r", encoding="utf-8") as file_handle:
            for raw_entry in file_handle.readlines():
                structured_entry = raw_entry.strip().split("\t")
                document = {
                    "_id": str(structured_entry[0]),
                    "drug_name": str(structured_entry[1]),
                    "active_ingredients": str(structured_entry[2]),
                    "strength": str(structured_entry[3]),
                    "dosage_form": str(structured_entry[4]),
                    "marketing_status": str(structured_entry[5]),
                    "therapeutic_equivalence": str(structured_entry[6]),
                    "reference_listed_drug": bool(structured_entry[7]),
                    "reference_standard": bool(structured_entry[8]),
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
            "drug_name": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            "active_ingredients": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            "strength": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            "dosage_form": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            "marketing_status": {"type": "keyword"},
            "te_code": {"type": "keyword"},
            "rld": {"type": "keyword"},
            "reference_standard": {"type": "keyword"},
        }
        return elasticsearch_mapping
