import json
import os
import glob

from biothings.utils.dataload import dict_sweep


def load_data_file(input_file):
    with open(input_file) as f:
        doc = json.load(f)

        studies = doc["studies"]
        for study in studies:
            study["_id"] = study['protocolSection']['identificationModule']['nctId']
            yield dict_sweep(study, ['','null', 'N/A', None, [], {}])