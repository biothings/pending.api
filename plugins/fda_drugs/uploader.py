"""
Uploader for the FDA Drugs data plugin

Handles the parsing of the document generated post_dump
from the dumper class instance
"""

import json
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
        structured_fda_drug_data = Path(data_folder).joinpath("FDA_DRUGS_GROUPING.json")
        with open(structured_fda_drug_data, "r", encoding="utf-8") as file_handle:
            joined_mapping = json.load(file_handle)
            for entry_map in joined_mapping:
                document = {
                    "_id": entry_map["unique_id"],
                    "anda": entry_map["application_number"],
                    "product_no": entry_map["product_number"],
                    "drug_name": entry_map["drug_name"],
                    "active_ingredients": entry_map["active_ingredient"],
                    "strength": entry_map["strength"],
                    "dosage_form": entry_map["dosage_form"],
                    "marketing_status": entry_map["marketing_status"],
                    "te_code": entry_map["te_code"],
                    "rld": entry_map["reference_drug"],
                    "rs": entry_map["reference_standard"],
                    "company": entry_map["company"],
                }
                yield document

    @classmethod
    def get_mapping(self) -> dict:
        """
        Elasticsearch mapping for representing the structured FDA drugs data
        Entry Structure:
        {
            <Application Number>
            <Product Number>
            <Drug Name>
            <Active Ingredients>
            <Strength>
            <Dosage Form/Route>
            <Marketing Status>
            <TE Code>
            <RLD>
            <RS>
            <Company>
        }
        """
        elasticsearch_mapping = {
            "anda": {"type": "keyword"},
            "product_no": {"type": "keyword"},
            "drug_name": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            "active_ingredients": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            "strength": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            "dosage_form": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            "marketing_status": {"type": "keyword"},
            "te_code": {"type": "keyword"},
            "rld": {"type": "boolean"},
            "rs": {"type": "boolean"},
            "company": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
        }
        return elasticsearch_mapping
