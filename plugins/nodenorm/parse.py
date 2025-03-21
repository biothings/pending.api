import json


def load_data_file(input_file: str):
    with open(input_file) as file_handle:

        buffer = []
        line = file_handle.readline()
        while line:
            doc = json.loads(line)
            doc["_id"] = doc["identifiers"][0]["i"]
            buffer.append(doc)

            if len(buffer) >= 1024:
                yield from buffer
                buffer = []
            line = file_handle.readline()

        if len(buffer) > 0:
            yield from buffer
            buffer = []
