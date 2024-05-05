"""
Uploader for the pubtator3 data plugin

Handles the parsing of the documents provided by [relation2pubtator3.gz]
"""

import itertools
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
        We have multiple different instances for entries

        instance 1: [MESH ID]
        >>> 33846804	treat	Chemical|MESH:D009828	Disease|MESH:D006528

        instance 2: [GENE ID]
        >>> 33846805	associate	Gene|5289	Gene|5562

        instance3: [MULTIPLE]
        >>> 26018198	associate	ProteinMutation|RS#:121908192;HGVS:c.581G>A;CorrespondingGene:2671	ProteinMutation|RS#:771809901;HGVS:c.373C>T;CorrespondingGene:2671
        >>> 20817350        cause   Disease|MESH:D000544    ProteinMutation|RS#:1800562;CorrespondingGene:3077
        """
        download_file_name = "relation2pubtator3"
        unstructured_relational_datafile = Path(data_folder).joinpath(download_file_name)
        unstructured_relational_datafile = unstructured_relational_datafile.resolve().absolute()
        with open(unstructured_relational_datafile, "r", encoding="utf-8") as file_handle:
            reading = True
            column_delimiter = "\t"
            entity_delimiter = "|"
            identifier_delimiter = ";"
            value_delimiter = ":"

            full_collection = set()
            while reading:
                raw_entry = file_handle.readline()
                reading = raw_entry != ""

                entry_collection = raw_entry.strip().split(column_delimiter)
                pmid = int(entry_collection[0])
                predicate = str(entry_collection[1]).upper()
                object_concept = str(entry_collection[2])
                subject_concept = str(entry_collection[3])

                object_entity_type, __, object_id = object_concept.partition(entity_delimiter)
                subject_entity_type, __, subject_id = subject_concept.partition(entity_delimiter)

                object_id_collection = object_id.split(identifier_delimiter)
                subject_id_collection = subject_id.split(identifier_delimiter)

                objects = []
                object_values = []
                subjects = []
                subject_values = []
                for object_id, subject_id in itertools.zip_longest(
                    object_id_collection, subject_id_collection, fillvalue=None
                ):
                    if object_id is not None:
                        sub_object_id = object_id.split(value_delimiter)
                        match len(sub_object_id):
                            case 1:
                                object_identifer_key = None
                                object_identifer_value = sub_object_id[0]
                            case 2:
                                object_identifer_key = sub_object_id[0]
                                object_identifer_value = sub_object_id[1]

                        objects.append(
                            {
                                "semantic_type_name": object_entity_type,
                                "identifier": {
                                    "key": object_identifer_key,
                                    "value": object_identifer_value
                                }
                            }
                        )
                        object_values.append(object_identifer_value)

                    if subject_id is not None:
                        sub_subject_id = subject_id.split(value_delimiter)
                        match len(sub_subject_id):
                            case 1:
                                subject_identifier_key = None
                                subject_identifier_value = sub_subject_id[0]

                            case 2:
                                subject_identifier_key = sub_subject_id[0]
                                subject_identifier_value = sub_subject_id[1]

                        subjects.append(
                            {
                                "semantic_type_name": subject_entity_type,
                                "identifier": {
                                    "key": subject_identifier_key,
                                    "value": subject_identifier_value
                                }
                            }
                        )
                        subject_values.append(subject_identifier_value)

                unique_id =(
                    f"{pmid}"
                    f"-{object_entity_type}"
                    f"-{'|'.join(object_values)}"
                    f"-{predicate}"
                    f"-{subject_entity_type}"
                    f"-{'|'.join(subject_values)}"
                )

                if len(objects) == 1:
                    objects = objects[0]
                if len(subjects) == 1:
                    subjects = subjects[0]

                full_collection.add(unique_id)

                document = {
                    "_id": unique_id,
                    "_version": 1,
                    "object": objects,
                    "pmid_count": 1,
                    "predicate": predicate,
                    "predication_count": 1,
                    "pmid": pmid,
                    "subject": subjects
                }
                yield document

    @classmethod
    def get_mapping(self) -> dict:
        mapping = {}

        return mapping
