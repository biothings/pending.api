"""
biothings.api plugin for parsing three different PFOCR "flavors"

flavors:
> all
> synoynms
> strict

"""


from pathlib import Path
import json


def _load_data(data_file):
    with open(data_file, "r", encoding="utf-8") as f:
        for line in f.readlines():
            doc = json.loads(line)
            if not isinstance(doc["associatedWith"]["pmc"], str):
                doc["associatedWith"].pop("pmc")
            yield doc


def load_pfocr_all(data_folder):
    data_file_name = "bte_chemicals_diseases_genes_all.ndjson"
    data_file = Path(data_folder) / data_file_name
    yield _load_data(str(data_file))


def load_pfocr_synoynms(data_folder):
    data_file_name = "bte_chemicals_diseases_genes_synoynms.ndjson"
    data_file = Path(data_folder) / data_file_name
    yield _load_data(str(data_file))


def load_pfocr_strict(data_folder):
    data_file_name = "bte_chemicals_diseases_genes_strict.ndjson"
    data_file = Path(data_folder) / data_file_name
    yield _load_data(str(data_file))
