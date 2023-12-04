import os
import json


def load_data(data_folder):
    file_path = os.path.join(data_folder, "bte_chemicals_diseases_genes.ndjson")
    with open(file_path) as f:
        for line in f.readlines():
            doc = json.loads(line)
            if not isinstance(doc['associatedWith']['pmc'], str):
                doc['associatedWith'].pop("pmc")
            yield doc
