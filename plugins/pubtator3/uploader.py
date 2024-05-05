"""
Uploader for the pubtator3 data plugin

Handles the parsing of the documents provided by [relation2pubtator3.gz]
"""

from pathlib import Path
from typing import Union

import biothings, config
import biothings.hub.dataload.uploader


class Pubtator3Uploader(biothings.hub.dataload.uploader.BaseSourceUploader):
    name = "pubtator3"
    __metadata__ = {
        "src_meta": {
            "url": "https://www.ncbi.nlm.nih.gov/research/pubtator3/",
            "license_url": "https://www.ncbi.nlm.nih.gov/home/about/policies/",
            "description": "Search entities & relations in 35+ million biomedical publications.",
        }
    }

    def load_data(data_folder: Union[str, Path]):
        """
        Expected data structure:
        >>> '33846804\ttreat\tChemical|MESH:D009828\tDisease|MESH:D006528\n'
        """
        chunk_size = 50000
        download_file_name = "relation2pubtator3"
        unstructured_relational_datafile = Path(data_folder).joinpath(download_file_name)
        unstructured_relational_datafile = unstructured_relational_datafile.resolve().absolute()
        with open(unstructured_relational_datafile, "r", encoding="utf-8") as file_handle:

            reading = True
            column_delimiter = "\t"
            entity_delimiter = "|"
            identifier_delimiter = ":"
            chunk = []
            while reading:
                raw_entry = file_handle.readline()
                reading = raw_entry != ""

                entry_collection = raw_entry.strip().split(column_delimiter)
                pmid = int(entry_collection[0])
                predicate = str(entry_collection[1]).upper()
                first_concept = str(entry_collection[2])
                second_concept = str(entry_collection[3])

                first_entity_type, __, first_identifer_id = first_concept.partition(entity_delimiter)
                second_entity_type, __, second_identifer_id = second_concept.partition(entity_delimiter)

                mesh, __, first_mesh_id = first_identifer_id.partition(identifier_delimiter)
                mesh, __, second_mesh_id = second_identifer_id.partition(identifier_delimiter)

                document = {
                    "_id": f"{first_mesh_id}-{predicate}-{second_mesh_id}",
                    "pmid": pmid,
                    "predicate": predicate,
                    "first_concept": first_concept,
                    "second_concept": second_concept,
                }
                print(document)
                yield document

    @classmethod
    def get_mapping(self) -> dict:
        mapping = {}

        return mapping
