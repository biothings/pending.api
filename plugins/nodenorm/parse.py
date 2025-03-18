import json


def load_data_file(input_file: str):
    with open(input_file) as file_handle:
        line = file_handle.readline()
        while line:
            doc = json.loads(line)
            doc["_id"] = doc["identifiers"][0]["i"]
            yield doc
            line = file_handle.readline()
