import pathlib
from typing import Union

import jsonlines

BUFFER_SIZE = 1024

PUBLICATIONS_FIELD_NAME = "publications"
PUBLICATIONS_INFO_FIELD_NAME = "publications_info"
PMID_FIELD_NAME = "pmid"


def flatten_publications(data: dict) -> list:
    pmid_list = data[PUBLICATIONS_FIELD_NAME]
    publications_info = data[PUBLICATIONS_INFO_FIELD_NAME]

    def extend_pub_info(pmid: str):
        pub_info = publications_info.get(pmid, None)
        if pub_info is not None:
            pub_info[PMID_FIELD_NAME] = pmid
            return pub_info

    return list(map(extend_pub_info, pmid_list))


def load_data_file(input_file: Union[pathlib.Path, str]) -> list:
    breakpoint()


def load_edges(data_folder: Union[str, pathlib.Path]):
    data_folder = pathlib.Path(data_folder).resolve().absolute()
    edge_file = data_folder.joinpath("edges.jsonl")
    with jsonlines.open(edge_file) as edge_reader:

        buffer = []

        for doc in edge_reader:
            buffer.append(doc)

            # make sure _id is a string
            doc["_id"] = str(doc["id"])

            # flatten nested publication_info field
            if PUBLICATIONS_FIELD_NAME in doc and PUBLICATIONS_INFO_FIELD_NAME in doc:
                doc[PUBLICATIONS_INFO_FIELD_NAME] = flatten_publications(doc)

            if len(buffer) == BUFFER_SIZE:
                yield from buffer
                buffer = []

        if len(buffer) > 0:
            yield from buffer


def load_nodes(data_folder: Union[str, pathlib.Path]):
    data_folder = pathlib.Path(data_folder).resolve().absolute()
    node_file = data_folder.joinpath("nodes.jsonl")
    with jsonlines.open(node_file) as node_reader:

        buffer = []

        for doc in node_reader:
            buffer.append(doc)

            # make sure _id is a string
            doc["_id"] = str(doc["id"])

            if len(buffer) == BUFFER_SIZE:
                yield from buffer
                buffer = []

        if len(buffer) > 0:
            yield from buffer
