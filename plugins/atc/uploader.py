"""
Uploader for the ATC data plugin
"""

from pathlib import Path
from typing import Union
import csv
import json
import logging

import biothings
import biothings.hub


logger = biothings.config.logger


class ATCUploader(biothings.hub.dataload.uploader.IgnoreDuplicatedSourceUploader):
    name = "atc"
    __metadata__ = {
        "src_meta": {
            "url": "https://atcddd.fhi.no/atc_ddd_index/",
            "license": "Attribution-ShareAlike-NonCommercial 4.0",
            "license_url": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
            "description": "Index of Anatomical Therapeutic Chemical (ATC) codes and Defined Daily Dose (DDD) units of measurment",
        }
    }

    def load_data(self, data_folder: Union[str, Path]):
        """
        Generator method for loading the CSV data and
        parsing into a dictionary via the csv module


        # Example structure
        atc_code,atc_name,ddd,uom,adm_r,note
        A,ALIMENTARY TRACT AND METABOLISM,NA,NA,NA,NA
        A01,STOMATOLOGICAL PREPARATIONS,NA,NA,NA,NA
        A01A,STOMATOLOGICAL PREPARATIONS,NA,NA,NA,NA
        A01AA,Caries prophylactic agents,NA,NA,NA,NA
        A01AA01,sodium fluoride,1.1,mg,O,0.5 mg fluoride
        A01AA02,sodium monofluorophosphate,NA,NA,NA,NA
        A01AA03,olaflur,1.1,mg,O,NA
        A01AA04,stannous fluoride,NA,NA,NA,NA
        ...

        ***Note***
        We're dropping most of the data because we only care about the ATC codes themselves.
        If we ever decide to include more the data be aware that duplicate ATC codes exist within
        the data and we'll have to utilize a different uploader strategy to merge them or create a
        new id generation scheme that will produce unique id values for each entry
        """
        filename = "WHO%20ATC-DDD%202021-12-03.csv"
        data_folder = Path(data_folder).absolute().resolve()
        data_file = data_folder.joinpath(filename)

        with open(str(data_file), "r", encoding="utf-8") as csvfile:
            dict_transformer = csv.DictReader(csvfile, delimiter=",")
            try:
                for row_mapping in dict_transformer:
                    document = {
                        "_id": row_mapping["atc_code"],
                        "code": row_mapping["atc_code"],
                        "name": row_mapping["atc_name"],
                    }
                    logger.debug("#%s %s", dict_transformer.line_num, row_mapping)
                    yield document
            except csv.Error as csv_error:
                logger.exception(csv_error)
                logger.error("Issue discovered with file %s @ line %s", data_file, dict_transformer.line_num)

    @classmethod
    def get_mapping(self) -> dict:
        """
        Elasticsearch mapping for representing the structured atc data

        Example structure:
        >>> atc_code,atc_name,ddd,uom,adm_r,note (Headers)

        (Entries)
        >>> A,ALIMENTARY TRACT AND METABOLISM,NA,NA,NA,NA
        >>> A01,STOMATOLOGICAL PREPARATIONS,NA,NA,NA,NA
        >>> A01A,STOMATOLOGICAL PREPARATIONS,NA,NA,NA,NA
        >>> A01AA,Caries prophylactic agents,NA,NA,NA,NA
        >>> A01AA01,sodium fluoride,1.1,mg,O,0.5 mg fluoride

        """
        elasticsearch_mapping = {
            "properties": {
                "code": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
                "name": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
            }
        }
        return elasticsearch_mapping
