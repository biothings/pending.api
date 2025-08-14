## pending-nodenorm

Hosted API of the nodenorm data provided by [RENCI](https://stars.renci.org/var/babel_outputs/2025mar31/compendia/)

File list (with smaller chunk files removed) as of March 12th 2025

```
AnatomicalEntity.txt                               24-Jan-2025 06:59            34710237
BiologicalProcess.txt                              24-Jan-2025 06:59            17659371
Cell.txt                                           24-Jan-2025 06:59             3397733
CellularComponent.txt                              24-Jan-2025 06:59             3189526
ChemicalEntity.txt                                 24-Jan-2025 06:59           113152551
ChemicalMixture.txt                                24-Jan-2025 06:59              154163
ComplexMolecularMixture.txt                        24-Jan-2025 06:59               40835
Disease.txt                                        24-Jan-2025 06:59           108426999
Drug.txt                                           24-Jan-2025 06:59            54718879
Gene.txt                                           24-Jan-2025 07:00         12693819719
GeneFamily.txt                                     24-Jan-2025 07:00             6239232
GrossAnatomicalStructure.txt                       24-Jan-2025 06:59             4146002
MacromolecularComplex.txt                          24-Jan-2025 07:00              129887
MolecularActivity.txt                              24-Jan-2025 07:00            58076135
MolecularMixture.txt                               24-Jan-2025 07:00          5622232715
OrganismTaxon.txt                                  24-Jan-2025 07:00           679718263
Pathway.txt                                        24-Jan-2025 07:00            14401268
PhenotypicFeature.txt                              24-Jan-2025 07:00            98947707
Polypeptide.txt                                    24-Jan-2025 07:00               34982
Protein.txt                                        24-Jan-2025 07:06         78143516945
Publication.txt                                    24-Jan-2025 07:07         14751156400
SmallMolecule.txt                                  24-Jan-2025 07:11         43006105240
umls.txt                                           24-Jan-2025 07:11           218530248
```


### Mapping

```JSON

{
    "type": {
        "normalizer": "keyword_lowercase_normalizer", 
        "type": "keyword"
    },
    "ic": {
        "type": "float"
    },
    "identifiers": {
        "properties": {
            "i": {
                "type": "keyword",
                "normalizer": "keyword_lowercase_normalizer",
                "copy_to": "all",  # default field
            },
            "l": {
                "type": "text",
                "fields": {
                    "raw": {
                        "type": "keyword", 
                        "ignore_above": 512
                    }
                },
                "copy_to": "all",  # default field
            },
            "d": {
                "type": "text"
            },
            "t": {
                "normalizer": "keyword_lowercase_normalizer",
                "type": "keyword"
            },
        }
    },
    "preferred_name": {
        "type": "text"
    },
    "taxa": {
        "normalizer": "keyword_lowercase_normalizer", 
        "type": "keyword"
    },
    "all": {"type": "text"},
}
```

### Elasticsearch Build Settings

```
{
    "num_replicas": 2,
    "num_shards": 10,
    "extra_index_settings": {
        "auto_expand_replicas": "0-all"
    }
}
```


### API

In order to validate elasticsearch as a backend, we want to mimic parts of the current nodenorm API
to compare the performance between the two. We currently want to support the following endpoints:


* `get_normalized_nodes` (GET | POST)

##### JSONSchema for `get_normalized_nodes`

```JSON
"CurieList": {
  "properties": {
    "curies": {
      "items": {
        "type": "string"
      },
      "type": "array",
      "minItems": 1,
      "title": "List of CURIEs to normalize"
    },
    "conflate": {
      "type": "boolean",
      "title": "Whether to apply gene/protein conflation",
      "default": true
    },
    "description": {
      "type": "boolean",
      "title": "Whether to return CURIE descriptions when possible",
      "default": false
    },
    "drug_chemical_conflate": {
      "type": "boolean",
      "title": "Whether to apply drug/chemical conflation",
      "default": false
    },
    "individual_types": {
      "type": "boolean",
      "title": "Whether to return individual types for equivalent identifiers",
      "default": false
    }
  },
  "type": "object",
  "required": [
    "curies"
  ],
  "title": "CurieList",
  "description": "Curie list input model",
  "example": {
    "curies": [
      "MESH:D014867",
      "NCIT:C34373"
    ],
    "conflate": true,
    "description": false,
    "drug_chemical_conflate": false
  }
}
```
