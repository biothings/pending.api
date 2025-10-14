import json
import pathlib

from typing import Union


def load_data_file(input_file: str):
    """
    Originally attempted to pass the conflation_database as a second argument, but ran into issues
    with the parallelized uploader worker handling multiple arguments

    The conflation_database is a static singular sqlite3 file located in the same directory as the
    data files as it's generated post-dump. We can just derived it at run-time from the provided
    data filepath

    Afterwards the data processing is straight forward, we effectively don't transform the state of
    the nodenorm files
    """
    input_file = pathlib.Path(input_file).absolute().resolve()
    yield from _load_data_file(input_file)


def _load_data_file(input_file: Union[str, pathlib.Path]):
    with open(input_file, encoding="utf-8") as file_handle:
        buffer = []
        line = file_handle.readline()
        while line:
            doc = json.loads(line)
            doc["_id"] = doc["curie"]
            try:
                doc["shortest_name_length"] = int(doc["shortest_name_length"])
            except (TypeError, ValueError):
                doc["shortest_name_length"] = 0

            try:
                doc["clique_identifier_count"] = int(doc["clique_identifier_count"])
            except (TypeError, ValueError):
                doc["clique_identifier_count"] = 0

            buffer.append(doc)

            if len(buffer) >= 1024:
                yield from buffer
                buffer = []
            line = file_handle.readline()

        if len(buffer) > 0:
            yield from buffer
            buffer = []
