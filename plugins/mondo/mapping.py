def get_customized_mapping(cls):
    mapping = {
        "mondo": {
            "properties": {
                "alt_id": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "ancestors": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "children": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "comment": {
                    "type": "text"
                },
                "consider": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "definition": {
                    "type": "text"
                },
                "descendants": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "disease_arises_from_feature": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "disease_causes_feature": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "disease_has_feature": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "disease_has_major_feature": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "disease_shares_features_of": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "disjoint_from": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "excluded_subClassOf": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "ncbitaxon": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "has_modifier": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "intersection_of": {
                    "type": "text"
                },
                'is_obsolete': {
                    'type': 'boolean'
                },
                "label": {
                    "type": "text",
                    "copy_to": [
                        "all"
                    ]
                },
                "mondo": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer",
                    "copy_to": [
                        "all"
                    ]
                },
                "never_in_taxon": {
                    "properties": {
                        "ncbitaxon": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "parents": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "part_of_progression_of_disease": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                "predisposes_towards": {
                    "properties": {
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                },
                'replaced_by': {
                    'type': 'keyword',
                    'normalizer': 'keyword_lowercase_normalizer'
                },
                "subset": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "synonym": {
                    "properties": {
                        "exact": {
                            "type": "text",
                            "copy_to": [
                                "all"
                            ]
                        },
                        "related": {
                            "type": "text"
                        }
                    }
                },
                "union_of": {
                    "type": "keyword",
                    "normalizer": "keyword_lowercase_normalizer"
                },
                "xrefs": {
                    "properties": {
                        "cohd": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "csp": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "dc": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "dermo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "doid": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer",
                            "copy_to": [
                                "all"
                            ]
                        },
                        "efo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "gard": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "gtr": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "hgnc": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "hp": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "icd10": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "icd10cm": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "icd11": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "icd9": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "icd9cm": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "icdo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "ido": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "iedb": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "kegg": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "loinc": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "meddra": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "medgen": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "mesh": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer",
                            "copy_to": [
                                "all"
                            ]
                        },
                        "mfomd": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "mondo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "mp": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "mth": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "ncit": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "ndfrt": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "nifstd": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "obi": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "ogms": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "omim": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "omimps": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "omop": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "oncotree": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "ordo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "orphanet": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "pato": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "pmid": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "reactome": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "scdo": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "sctid": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "sctid_2010_1_31": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "umls": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "umls_cui": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "url": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "wikidata": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        },
                        "wikipedia": {
                            "type": "keyword",
                            "normalizer": "keyword_lowercase_normalizer"
                        }
                    }
                }
            }
        }
    }
    return mapping
