import json

BUFFER_SIZE = 1024

PUBLICATIONS_FIELD_NAME= 'publications'
PUBLICATIONS_INFO_FIELD_NAME= 'publications_info'
PMID_FIELD_NAME= 'pmid'

def flatten_publications(data):
    pmid_list = data[PUBLICATIONS_FIELD_NAME]
    publications_info = data[PUBLICATIONS_INFO_FIELD_NAME]

    def extend_pub_info(pmid: str):
        pub_info = publications_info[pmid]
        pub_info[PMID_FIELD_NAME] = pmid
        return pub_info

    return list(map(extend_pub_info, pmid_list))


def load_data_file(input_file: str):
    with open(input_file, encoding="utf-8") as file_handle:

        buffer = []

        for line in file_handle:
            doc = json.loads(line)
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