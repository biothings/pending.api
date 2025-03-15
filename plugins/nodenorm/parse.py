import json


def load_data_file(input_file: str):
    with open(input_file) as file_handle:
        for line in file_handle.readlines():
            doc = json.loads(line)
            doc["_id"] = doc["preferred_name"]
            yield doc
