def pfocr_mapping(cls):
    """
    Elasticsearch mapping for representing the structured pfocr data

    All three flavors share the same structure and therefor the same mapping

    Examples Entries:
    pfocr_all:
    {
        "_id": "PMC10003241__ijms-24-04893-g003",
        "associatedWith": {
            "title": "Metabolic Features of Osteoblasts: Implications for Multiple Myeloma (MM) Bone Disease",
            "pfocrUrl": "https://pfocr.wikipathways.org/figures/PMC10003241__ijms-24-04893-g003.html",
            "figureUrl": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10003241/bin/ijms-24-04893-g003.jpg",
            "pmc": "PMC10003241",
            "mentions": {
                "chemicals": {
                    "mesh": [
                        "C076685",
                        "D005978",
                        "C065987",
                        "C528802",
                        "D005947",
                        "C108952",
                        "D005227",
                        "D000255",
                        "D011773",
                        "C000589078"
                    ]
                },
                "diseases": {
                    "mesh": [
                        "D011488"
                    ]
                },
                "genes": {
                    "ncbigene": [
                        "51761",
                        "121340",
                        "7482",
                        "80326",
                        "7481",
                        "2475",
                        "7477",
                        "7478",
                        "4040",
                        "253260",
                        "7483",
                        "6507",
                        "7484",
                        "9056",
                        "1376",
                        "57521",
                        "1301",
                        "2744",
                        "79109",
                        "7479",
                        "1277",
                        "3069",
                        "7480",
                        "1374",
                        "7472",
                        "7476",
                        "6517",
                        "56994",
                        "10254",
                        "8321",
                        "8324",
                        "4041",
                        "8326",
                        "6515",
                        "27165",
                        "207",
                        "7475",
                        "4281",
                        "7471",
                        "81029",
                        "208",
                        "54407",
                        "8322",
                        "4846",
                        "8325",
                        "10000",
                        "2535",
                        "54361",
                        "7976",
                        "8323",
                        "7884",
                        "6510",
                        "860",
                        "3952",
                        "473",
                        "64223",
                        "7474",
                        "566",
                        "7855",
                        "6513",
                        "50865",
                        "11211",
                        "51384",
                        "7473",
                        "27",
                        "89780",
                        "4843",
                        "440",
                        "4842"
                    ]
                }
            }
        }
    }

    pfocr_strict:
    {
        "_id": "PMC10003241__ijms-24-04893-g003",
        "associatedWith": {
            "title": "Metabolic Features of Osteoblasts: Implications for Multiple Myeloma (MM) Bone Disease",
            "pfocrUrl": "https://pfocr.wikipathways.org/figures/PMC10003241__ijms-24-04893-g003.html",
            "figureUrl": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10003241/bin/ijms-24-04893-g003.jpg",
            "pmc": "PMC10003241",
            "mentions": {
                "chemicals": {
                    "mesh": [
                        "C076685",
                        "D005978",
                        "C065987",
                        "C528802",
                        "D005947",
                        "C108952",
                        "D005227",
                        "D000255",
                        "D011773",
                        "C000589078"
                    ]
                },
                "diseases": {
                    "mesh": [
                        "D011488"
                    ]
                },
                "genes": {
                    "ncbigene": [
                        "2744",
                        "1277",
                        "4040",
                        "54407",
                        "6507",
                        "6510",
                        "9056",
                        "860",
                        "440",
                        "4041"
                    ]
                }
            }
        }
    }

    pfocr_synoynms:
    {
        "_id": "PMC10003241__ijms-24-04893-g003",
        "associatedWith": {
            "title": "Metabolic Features of Osteoblasts: Implications for Multiple Myeloma (MM) Bone Disease",
            "pfocrUrl": "https://pfocr.wikipathways.org/figures/PMC10003241__ijms-24-04893-g003.html",
            "figureUrl": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10003241/bin/ijms-24-04893-g003.jpg",
            "pmc": "PMC10003241",
            "mentions": {
                "chemicals": {
                    "mesh": [
                        "C076685",
                        "D005978",
                        "C065987",
                        "C528802",
                        "D005947",
                        "C108952",
                        "D005227",
                        "D000255",
                        "D011773",
                        "C000589078"
                    ]
                },
                "diseases": {
                    "mesh": [
                        "D011488"
                    ]
                },
                "genes": {
                    "ncbigene": [
                        "51761",
                        "121340",
                        "4040",
                        "6507",
                        "9056",
                        "1376",
                        "1301",
                        "2744",
                        "1277",
                        "3069",
                        "1374",
                        "6517",
                        "56994",
                        "10254",
                        "27165",
                        "4041",
                        "6515",
                        "207",
                        "4281",
                        "54407",
                        "7884",
                        "6510",
                        "860",
                        "3952",
                        "473",
                        "566",
                        "6513",
                        "50865",
                        "27",
                        "4843",
                        "440",
                        "4842"
                    ]
                }
            }
        }
    }

    """
    elasticsearch_mapping = {
        "associatedWith": {
            "properties": {
                "title": {"type": "keyword"},
                "pfocrUrl": {"type": "keyword"},
                "figureUrl": {"type": "keyword"},
                "pmc": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"},
                "mentions": {
                    "properties": {
                        "chemicals": {
                            "properties": {"mesh": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"}}
                        },
                        "diseases": {
                            "properties": {"mesh": {"type": "keyword", "normalizer": "keyword_lowercase_normalizer"}}
                        },
                        "genes": {
                            "properties": {
                                "bcbigene": {
                                    "type": "keyword",
                                }
                            }
                        },
                    }
                },
            }
        },
    }

    return elasticsearch_mapping
