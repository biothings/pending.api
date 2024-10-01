def pfocr_mapping(cls):
    """
    Elasticsearch mapping for representing the structured pfocr data

    All three flavors share the same structure and therefor the same mapping

    Examples Entries:
    pfocr_all:
    {
        "_id": "PMC10088895__jcav14p0850g001",
        "associatedWith": {
            "title": "PD-1/PD-L1 pathway plays a role in immunosuppression",
            "pfocrUrl": "https://pfocr.wikipathways.org/figures/PMC10088895__jcav14p0850g001.html",
            "figureUrl": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10088895/bin/jcav14p0850g001.jpg",
            "pmc": "PMC10088895",
            "mentions": {
                "chemicals": {
                    "mesh": [],
                    "chebi": [
                        "63620",
                        "28398"
                    ]
                },
                "diseases": {
                    "mesh": [],
                    "doid": []
                },
                "genes": {
                    "ncbigene": [
                        "940",
                        "23595",
                        "6957",
                        "7535",
                        "5133",
                        "3845",
                        "5290",
                        "2048",
                        "5291",
                        "27040",
                        "207",
                        "5595",
                        "5624",
                        "8503",
                        "3265",
                        "5293",
                        "100526842",
                        "30849",
                        "5605",
                        "146850",
                        "23533",
                        "83985",
                        "6965",
                        "10000",
                        "5781",
                        "208",
                        "29126",
                        "6964",
                        "5294",
                        "5604",
                        "5295",
                        "324",
                        "3107",
                        "5594",
                        "1493",
                        "6139",
                        "6962",
                        "6955",
                        "4893",
                        "5728",
                        "5296",
                        "5609"
                    ]
                }
            }
        }
    }

    pfocr_strict:
    {
        "_id": "PMC10088895__jcav14p0850g001",
        "associatedWith": {
            "title": "PD-1/PD-L1 pathway plays a role in immunosuppression",
            "pfocrUrl": "https://pfocr.wikipathways.org/figures/PMC10088895__jcav14p0850g001.html",
            "figureUrl": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10088895/bin/jcav14p0850g001.jpg",
            "pmc": "PMC10088895",
            "mentions": {
                "chemicals": {
                    "mesh": [],
                    "chebi": [
                        "63620",
                        "28398"
                    ]
                },
                "diseases": {
                    "mesh": [],
                    "doid": []
                },
                "genes": {
                    "ncbigene": [
                        "940",
                        "7535",
                        "324",
                        "5728",
                        "27040"
                    ]
                }
            }
        }
    }

    pfocr_synoynms:
    {
        "_id": "PMC10088895__jcav14p0850g001",
        "associatedWith": {
            "title": "PD-1/PD-L1 pathway plays a role in immunosuppression",
            "pfocrUrl": "https://pfocr.wikipathways.org/figures/PMC10088895__jcav14p0850g001.html",
            "figureUrl": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10088895/bin/jcav14p0850g001.jpg",
            "pmc": "PMC10088895",
            "mentions": {
                "chemicals": {
                    "mesh": [],
                    "chebi": [
                        "63620",
                        "28398"
                    ]
                },
                "diseases": {
                    "mesh": [],
                    "doid": []
                },
                "genes": {
                    "ncbigene": [
                        "940",
                        "23595",
                        "7535",
                        "5133",
                        "5290",
                        "2048",
                        "5291",
                        "27040",
                        "207",
                        "5624",
                        "5293",
                        "100526842",
                        "83985",
                        "5781",
                        "29126",
                        "5294",
                        "324",
                        "3107",
                        "5594",
                        "1493",
                        "6139",
                        "6962",
                        "5728",
                        "5609"
                    ]
                }
            }
        }
    }
    """
    elasticsearch_mapping = {
        "associatedWith": {
            "properties": {
                "title": {"type": "text"},
                "pfocrUrl": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                "figureUrl": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                "pmc": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                "mentions": {
                    "properties": {
                        "chemicals": {
                            "properties": {
                                "mesh": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                                "chebi": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                            }
                        },
                        "diseases": {
                            "properties": {
                                "mesh": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                                "doid": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                            }
                        },
                        "genes": {
                            "properties": {
                                "ncbigene": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"}
                            }
                        },
                    }
                },
            }
        }
    }

    return elasticsearch_mapping
