import re
import os.path
import json
from collections import defaultdict
from biothings.utils.common import open_anyfile
from biothings.utils.dataload import dict_sweep

SKIP_ROWS = 15   # number of rows to skip
HEADER_ROW = 15  # zero-indexed header row
DESIRED_OBJECT_TYPES = [
    "gene"
]

def load_data(data_folder):
    agr_file = os.path.join(data_folder, "DISEASE-ALLIANCE_COMBINED_47.tsv.gz")
    i = -1
    entries = defaultdict(dict)


    with open_anyfile(agr_file, "r") as file:
        for line in file:
            i += 1
            if i < SKIP_ROWS:
                continue
            elif i == HEADER_ROW:
                # convert headers to lowercase, underscore_delimited
                header = [
                    re.sub(r"(.)([A-Z])", r"\1_\2", colname).lower()
                    for colname in
                    line.rstrip('\n').split('\t')
                ]
                continue

            row = line.rstrip('\n').split('\t')
            if row[2] not in DESIRED_OBJECT_TYPES:
                continue

            # Comments below correspond to original column names
            entries[row[3]]["_id"] = row[3]  # DBObjectID
            if "agr" not in entries[row[3]]:
                entries[row[3]]["agr"] = {}
            entry = entries[row[3]]["agr"]
            entry[header[0]] = row[0]        # Taxon
            entry[header[1]] = row[1]        # SpeciesName
            entry["symbol"] = row[4]         # originally DBObjectSymbol

            if row[5] not in entry:
                entry[row[5]] = []

            entry[row[5]].append(dict_sweep({  # AssociationType
                "doid": row[6],                # DOID
                "term_name": row[7],           # DOtermName
                header[8]: list(
                    filter(len, row[8].split("|"))
                ),                             # WithOrthologs
                "inferred_from_id": row[9],    # InferredFromID
                header[10]: row[10],           # InferredFromSymbol
                header[11]: row[11],           # EvidenceCode
                header[12]: row[12],           # EvidenceCodeName
                header[13]: row[13],           # Reference
                header[14]: row[14],           # Date
                header[15]: row[15]            # Source
            }, remove_invalid_list=True))

    for doc in entries.values():
        yield dict_sweep(doc, remove_invalid_list=True)
