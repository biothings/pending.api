import os
from os import path



def create_configs():
    cwd = path.dirname(__file__)
    os.chdir(cwd)
    import requests
    configs = requests.get("https://biothings.ncats.io/api/list").json()
    assert configs["status"] == "ok"
    with open('__init__.py', 'a') as init:

        for config in configs["result"]:
            api_name = config["_id"]
            es_host = config["config"]["es_host"]
            es_index = config["config"]["index"]
            es_type = config["config"]["doc_type"]
            init.write("from . import {}\n".format(api_name.lower()))
            with open(api_name.lower() + '.py', 'w') as file:
                file.write("""
ES_HOST = '{}'
ES_INDEX = '{}'
ES_DOC_TYPE = '{}'

API_PREFIX = '{}'
API_VERSION = ''
""".format(es_host, es_index, es_type, api_name.lower()))
        

if __name__ == '__main__':
    create_configs()
