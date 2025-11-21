## pending-nodenorm

Hosted API of the nodenorm data provided by [RENCI](https://stars.renci.org/var/babel_outputs/2025mar31/compendia/)

File list (with smaller chunk files removed) as of September 2nd 2025

```
AnatomicalEntity.txt                               02-Sep-2025 03:54            38586258
BiologicalProcess.txt                              02-Sep-2025 03:54            17470772
Cell.txt                                           02-Sep-2025 03:54             3524366
CellLine.txt                                       02-Sep-2025 03:54             6496531
CellularComponent.txt                              02-Sep-2025 03:54             3190094
ChemicalEntity.txt                                 02-Sep-2025 03:54           511093905
ChemicalMixture.txt                                02-Sep-2025 03:54              153385
ComplexMolecularMixture.txt                        02-Sep-2025 03:54               41199
Disease.txt                                        02-Sep-2025 03:54           109100284
Drug.txt                                           02-Sep-2025 03:54            57010182
Gene.txt                                           02-Sep-2025 03:55         15601671131
GeneFamily.txt                                     02-Sep-2025 03:55             6255568
GrossAnatomicalStructure.txt                       02-Sep-2025 03:54             4166218
MacromolecularComplex.txt                          02-Sep-2025 03:55              129887
MolecularActivity.txt                              02-Sep-2025 03:55            59513602
MolecularMixture.txt                               02-Sep-2025 03:56          5959903492
OrganismTaxon.txt                                  02-Sep-2025 03:56           697224103
Pathway.txt                                        02-Sep-2025 03:56            14356578
PhenotypicFeature.txt                              02-Sep-2025 03:56            99273513
Polypeptide.txt                                    02-Sep-2025 03:56               30486
Protein.txt                                        02-Sep-2025 03:59         78029682489
Publication.txt                                    02-Sep-2025 04:01         15169616284
SmallMolecule.txt                                  02-Sep-2025 04:03         44485987213
umls.txt                                           02-Sep-2025 04:03           216944636
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

In order to validate Elasticsearch as a backend, we want to mimic parts of the current nodenorm API
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
      "NCIT:C34373"sequentially download all the files
    ],
    "conflate": true,
    "description": false,
    "drug_chemical_conflate": false
  }
}
```


## Optimizations

Due to the amount of data, performance requirements, and custom behavior desired for this API, there
were several optimizations that were needed in order for this to run relative efficiently

### Downloading
There are ~160 GB of data. On the file server these are uncompressed files, so that's raw text we
have to do download from the FTP server. At the time of designing the plugin, the dump would take
several hours to download as the data wasn't uniformed distributed. Two of the files comprise more
than 75% of the data stored on the FTP server. So these two files were the bottlenecks over the
network. We created the NodeNormDumper to take advantage of Content-Length
[header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Length) 
so we could acquire the size in bytes of the body. Knowing the size in bytes allows us to request
the file in discrete chunks if we specify the byte start and byte end of the amount of data we wish
to retrieve. We do this via the Range [header](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Range_requests),
which allows to breakup the files into as many chunks as we want to download. By default we specify
the number of chunks as 10. For smaller files this provides minimal to potential worse performance
as the overhead of sending the HEAD request, getting the discrete chunk sizes, and then sending 10
multi-threaded RANGE requests would be slightly slower than simply sending 1 GET request to download
the entire file. However, most of the files are sufficiently large that we benefit from this
chunking method. We take special care for the largest files, by specifying the number of chunks
anywhere from 50 to 200 separate chunks. The block diagram below graphical displays an example of
how we download 1 file

###### Block Diagram for Range Dumping

```shell
                  │filesystem                         │network
                  │                                   │
                  │                          HEAD     │
                  │         ┌───────────────┐REQUEST  │         ┌───────────────┐
                  │         │biothings      ├─────────┼────────►│RENCI FTP      │
                  │         │backend        │         │         │server         │
                  │         │               │         │         │               │
                  │         │               │         │     HEAD│               │
                  │         │               │         │ RESPONSE│               │
                  │         │               │◄────────┼─────────┤               │
                  │         └───────┬───────┘         │         │               │
                  │                 │                 │         │               │
                  │                 │content-length   │         │               │
                  │                 │header           │         │               │
                  │                 │                 │         │               │
                  │         ┌───────┴───────┐         │         │               │
                  │         ┼thread0        ┼─────────┼────────►│               │
                  │         ┼───────────────┤   ▲     │         │               │
┌──────────┐      │         ┼thread1        ┼───┼─────┼────────►│               │
│recombined│◄─────┼───────  ┼───────────────┤   │   ▲ │         │               │
│file      │      │         ┼      ..       ┼───┼───┼─┼────────►│               │
└──────────┘      │         ┼───────────────┤   │   │ │         │               │
                  │         ┼threadN        ┼───┼───┼─┼────────►│               │
                  │         └───────────────┘   │   │ │ ▲       │               │
                  │                             │   │ │ │       └───────────────┘
                                                │   │   │
                                                │   │   │
                                  ┌─────────────┤   │   │
                                  │ GET REQUEST │   │   │
                                  │  filepart0  │   │   │
                                  └─────────────┘   │   │
                                      ┌─────────────┤   │
                                      │ GET REQUEST │   │
                                      │  filepart1  │   │
                                      └─────────────┘   │
                                          ┌─────────────┤
                                          │ GET REQUEST │
                                          │  filepartN  │
                                          └─────────────┘
```


### Uploading (MongoDB)

Originally we used the `ParallelizedSourceUploader` when uploading to MongoDB. Again, due to the
non-uniform nature of the data, this still meant that 2 of the files would make up the majority of
the upload time and likely not save that much time. The largest file at this time, `Protein.txt`, is
73 GB uncompressed. The entire directory is 156 GB, which means that one file is 46.7% of the data.
That means we're still having to sequentially upload 73 GB of data to the database in batches of
10000. Even on su06, this task is entirely network bound the way it's currently framed.  

Instead we need a way to re-frame the problem so that we don't have a singular process stuck
processing too much data. We have two things that we can benefit from that allows us to chunk this
problem more discretely

1. The data is jsonlines, so each line is a "record" that we want to upload to either a MongoDB
   collection or an Elasticsearch index
2. We can upload in any order as we have no preference for the data ordering once it's in the
   collection

So what we can do is determine how many partitions we want from each file. Then at the beginning of
the upload phase, we read the entire file and store the file offset at certain discrete points
representing one of the chunks. These offsets can be stored as arguments to our parallel worker,
where we now have a pool of workers constantly working on a discrete chunk of the data and uploading
to MongoDB in parallel. This cut what was originally a 4 hour upload into ~1 hour to upload to the
database. Further optimizations could be performed by analyzing all files and finding a chunk size
that makes each task identical in terms of the amount of data processed along with playing with the
bulk_write size to determine the best document size for uploading. MongoDB documentation dictates
this size should be between 1000-10000 documents, so we choose 5000 to stay in the middle, but no
empirical testing was performed to evaluate this guideline. There is a blocking portion at the
beginning where we wait for all files to have finished being analyzed for offsets where we could
likely start faster on a per-file completion basis 


### Post Upload Processing (MongoDB)

There is an unfortunate issue at the moment with the current Babel release in that conflation
propagates duplicate CURIE identifiers to the compendium data. Due to the nature of how we query the
data in Elasticsearch, we assume there's a 1-1 mapping for CURIE identifier (`identifier.i`) to
document. Our terms query to Elasticsearch is formatted like the following:

```JSON
{
  "bool": {
    "filter": [
      {
        "terms": {"identifiers.i": curies}
      }
    ]
  }
}
```

To demonstrate what happens if this assumption about a 1-1 mapping between `identifiers.i` and
documents does not hold imagine the following example:


```JSON
{
  "bool": {
    "filter": [
      {
        "terms": {"identifiers.i": [standard_curie0, duplicate_curie0, standard_curie1]}
      }
    ]
  }
}
```

In this case we have 3 CURIES (`standard_curie0`, `duplicate_curie0`, `standard_curie1`). We know
that `standard_curie0` and `standard_curie` have an exact match to 1 document. We know that
`duplicate_curie0` matches to 2 documents within the index. However, due to our initial assumption,
we specify a size of 3 when querying Elasticsearch to ensure we only get the expected 3 documents
back. This means that the document for `standard_curie1` is never returned and instead maps to the
second document associated with the `duplicate_curie0`. We could increase the size constraint, but
this won't solve the issue as any duplicated document will propagate the incorrect document to the
next CURIE in the terms chain. This leads to a very annoying bug to track as our results no longer
map and in a 1000 term query it's difficult to pinpoint which CURIE is the offending instance.


So how do we fix this?

###### sqlite3 identifiers table
In our newly created worker instance for the nodenorm uploader, we create a sqlite3 table. Fairly
basic table that tracks all identifiers we find across all documents. If we find a duplicate
identifier, we increment the count to track all duplicated CURIE's.

```SQL
CREATE TABLE IF NOT EXISTS identifiers(identifier text PRIMARY KEY NOT NULL, count INT DEFAULT 1);
```

This produces a behemoth of a table, with around 680 million identifiers and table taking about 50
GB of space on the file-system. Writing to it as we store the identifiers from each task is now the
bottleneck of the upload process as we cannot parallelize the writes to sqlite3 and we're writing
about 5 million records per process for some of the bigger tasks. There could be some configuration
settings that alleviate this bottleneck, but I haven't investigated that yet. Given this is also a
temporary solution as the data upstream will eventually resolve this issue I don't wish to devote
too much time to optimize this solution. 

Either way, once we have this table we need to also create an index on it so we can actually
efficiently get all the documents without it taking forever. This will further balloon the size of
the table, but it saves a tremendous amount of time. Around this time in the uploading process we
also create an index for the MongoDB collection. We don't require partial searches so we create a
regular index over a search index, and we only need it on `identifiers.i`. This also provides a
tremendous speedup as we're going to have to read each duplicate CURIE correction one-by-one to
rectify them as we cannot easily do bulk-reads in the same way as writes with MongoDB. 

This leads to the different ways we have to resolve the duplicate CURIES:

* Duplicate CURIE case 1: Identical documents besides the typing

We get the exact same document, but the typing is different depending on the conflation. We're
automatically merging this and need a way of representing the type, it normally doesn't have the
`biolink:Protein` typing

Log: `Replace 1 document to trim all identifiers except the first due to them all being identical: {'_id': 'ENSEMBL:YDR387C', 'type': ['biolink:Protein', 'biolink:Gene'], 'ic': 0.0, 'identifiers': [{'i': 'ENSEMBL:YDR387C', 'd': [], 't': [], 'c': {'gp': None, 'dc': None}}], 'preferred_name': '', 'taxa': []}`

Examining the compendium files we have the following two documents:

```shell
❯ rg "ENSEMBL:YDR387C"
Gene.txt 
39519836:{"type": "biolink:Gene", "ic": null, "identifiers": [{"i": "ENSEMBL:YDR387C", "d": [], "t": []}], "preferred_name": "", "taxa": []}

Protein.txt
143744272:{"type": "biolink:Protein", "ic": null, "identifiers": [{"i": "ENSEMBL:YDR387C", "d": [], "t": []}], "preferred_name": "", "taxa": []}
```

* Duplicate CURIE case 2: Duplication across documents with one being an obvious subset

In this case we do have one identifier across 2 documents. Pulling an example from the logs: `MESH:C086888`.
Log: `Delete 1 document: {'_id': 'MESH:C086888', 'type': 'biolink:ChemicalEntity', 'ic': 0.0, 'identifiers': [{'i': 'MESH:C086888', 'l': 'USO1 protein, S cerevisiae', 'd': [], 't': [], 'c': {'gp': None, 'dc': None}}], 'preferred_name': 'USO1 protein, S cerevisiae', 'taxa': []}`

Examining the compendium files we have the following two documents:

```shell
ChemicalEntity.txt
1985468:{"type": "biolink:ChemicalEntity", "ic": null, "identifiers": [{"i": "MESH:C086888", "l": "USO1 protein, S cerevisiae", "d": [], "t": []}], "preferred_name": "USO1 protein, S cerevisiae", "taxa": []}

Protein.txt
48774369:{"type": "biolink:Protein", "ic": null, "identifiers": [{"i": "UMLS:C0254024", "l": "USO1 protein, S cerevisiae", "d": [], "t": []}, {"i": "MESH:C086888", "l": "USO1 protein, S cerevisiae", "d": [], "t": []}], "preferred_name": "USO1 protein, S cerevisiae", "taxa": []}
```

In this case we have all of the information from the ChemicalEntity document encapsulated within the
Protein document. We simply have to ensure we properly handle the type


* Duplicate CURIE case 3: Duplication without a clear merge strategy as neither document is a subset of the other

Log: `Unable to resolve conflict | MESH:C000599672`
 Unable to resolve conflict | MESH:D020652

Examining the compendium files we have the following two documents:

```shell
❯ rg 'MESH:D020652'
SmallMolecule.txt
91355371:{"type": "biolink:SmallMolecule", "ic": null, "identifiers": [{"i": "PUBCHEM.COMPOUND:148754", "l": "Peptide Elongation Factor 2", "d": [], "t": []}, {"i": "MESH:D020652", "l": "Peptide Elongation Factor 2", "d": [], "t": []}, {"i": "CAS:55739-78-1", "l": "", "d": [], "t": []}, {"i": "INCHIKEY:RYXGAWJESREXQK-UHFFFAOYSA-N", "l": "", "d": [], "t": []}], "preferred_name": "Peptide Elongation Factor 2", "taxa": []}

Protein.txt
81067869:{"type": "biolink:Protein", "ic": null, "identifiers": [{"i": "UMLS:C0059037", "l": "Peptide Elongation Factor 2", "d": [], "t": []}, {"i": "MESH:D020652", "l": "Peptide Elongation Factor 2", "d": [], "t": []}], "preferred_name": "Peptide Elongation Factor 2", "taxa": []}
```

Solution: Ensure that at least one clique is Protein. If at least one is Protein, then remove all
instances from the non-protein clique that collide 

* Duplicate CURIE case 4: 1 document with multiple duplicate identifiers


I think this is a weird sub-case specific to `MacromolecularComplex.txt`. All entries in this
document have a duplicate identifier. This shouldn't change much, but it is slightly more
efficient to prune the document before upload

```JSONLINES
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-232", "d": [], "t": []}, {"i": "ComplexPortal:CPX-232", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-778", "d": [], "t": []}, {"i": "ComplexPortal:CPX-778", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-1731", "d": [], "t": []}, {"i": "ComplexPortal:CPX-1731", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-1279", "d": [], "t": []}, {"i": "ComplexPortal:CPX-1279", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-535", "d": [], "t": []}, {"i": "ComplexPortal:CPX-535", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-950", "d": [], "t": []}, {"i": "ComplexPortal:CPX-950", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-301", "d": [], "t": []}, {"i": "ComplexPortal:CPX-301", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-1613", "d": [], "t": []}, {"i": "ComplexPortal:CPX-1613", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-5461", "d": [], "t": []}, {"i": "ComplexPortal:CPX-5461", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-1856", "d": [], "t": []}, {"i": "ComplexPortal:CPX-1856", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-775", "d": [], "t": []}, {"i": "ComplexPortal:CPX-775", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-3172", "d": [], "t": []}, {"i": "ComplexPortal:CPX-3172", "d": [], "t": []}], "preferred_name": "", "taxa": []}
{"type": "biolink:MacromolecularComplex", "ic": null, "identifiers": [{"i": "ComplexPortal:CPX-695", "d": [], "t": []}, {"i": "ComplexPortal:CPX-695", "d": [], "t": []}], "preferred_name": "", "taxa": []}
```

