def get_customized_mapping(cls):
    mapping = {
        "parents": {
            "normalizer": "keyword_lowercase_normalizer",
            "type": "keyword"
        },
        "ancestors": {
            "normalizer": "keyword_lowercase_normalizer",
            "type": "keyword"
        },
        "synonym": {
            "properties": {
                "exact": {
                    "type": "text"
                }
            }
        },
        "xrefs": {
            "properties": {
                "imdrf": {
                    "normalizer": "keyword_lowercase_normalizer",
                    "type": "keyword"
                },
                "uberon": {
                    "normalizer": "keyword_lowercase_normalizer",
                    "type": "keyword"
                }
            }
        },
        "is_obsolete": {
            "type": "boolean"
        },
        "children": {
            "normalizer": "keyword_lowercase_normalizer",
            "type": "keyword"
        },
        "descendants": {
            "normalizer": "keyword_lowercase_normalizer",
            "type": "keyword"
        },
        "definition": {
            "type": "text"
        },
        "label": {
            "type": "text"
        }
    }
    return mapping
