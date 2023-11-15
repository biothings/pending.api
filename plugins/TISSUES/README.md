 # TISSUES Data Plugin for `pending.biothings.io`  
  
Data plugin for the [TISSUES Database](https://tissues.jensenlab.org/About).  
  
- **Association centric**  document    
- The parser only imports human datafiles --_other species files are available_

<details>
<summary>Example Record</summary>
  
```  

{
    "_id": "CLDB:0007242_00000090",
    "subject": {
        "id": "CLDB:0007242",
        "name": "COV-644"
    },
    "association": {
        "tissue_name": "COV-644",
        "zscore": "2.239",
        "confidence": "1.120",
        "category": "textmining"
    },
    "object": {
        "ensembl": "hsa-miR-892a",
        "symbol": "hsa-miR-892a"
    }
}

```

</details>