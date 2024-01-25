# Data Plugin

This repo is the Biothings plugin for [repoDB](https://unmtid-shinyapps.net/shiny/repodb/) _v2.0-SNAPSHOT_ data. The requirements were discussed in [smartAPI - Issue#85](https://github.com/SmartAPI/smartAPI/issues/85).

A sample document for `Brolucizumab` is shown below:

```python
{
    "_id": "DB14864_C0271084",
    "drug": {
        "drugbank": "DB14864",
        "name": "Brolucizumab"
    },
    "indication": {
        "name": "Exudative age-related macular degeneration",
        "umls": "C0271084"
    },
    "trials": [
        {
            "status": "approved"
        }
    ]
}
```

# Side note: why we chose to manually upload the data files

Currently we use 2 data files:

1. `full.csv`, downloadble from https://unmtid-shinyapps.net/shiny/repodb/. 
2. `drugbank vocabulary.csv` (note the space in the filename), which is from unzipping `drugbank_all_drugbank_vocabulary.csv.zip` ([direct download link](https://go.drugbank.com/releases/5-1-9/downloads/all-drugbank-vocabulary)) from [DrugBank Release Version 5.1.9 - Open Data](https://go.drugbank.com/releases/5-1-9#open-data).

The problem with downloading `full.csv` is that, every time the download button is clicked on the repoDB webpage, a session id is generated as part of the download link, like: 

```txt
https://unmtid-shinyapps.net/shiny/repodb/session/9f5dcbef21859438b1c0cea784bde839/download/downloadFull?w=
```

We are not clear if the session id would expire or become invalid, so we chose not to use this kind of direct download links in the manifest.json.

For the drugbank vocabulary, the direct download link `https://go.drugbank.com/releases/5-1-9/downloads/all-drugbank-vocabulary` works well for browser users. It will be redirected to an Amazon S3 link like: 

```
https://drugbank.s3.us-west-2.amazonaws.com/public_downloads/downloads/000/005/940/original/drugbank_all_drugbank_vocabulary.csv.zip?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAJTZC3DSCEEG75A6Q%2F20220802%2Fus-west-2%2Fs3%2Faws4_request&X-Amz-Date=20220802T214251Z&X-Amz-Expires=30&X-Amz-SignedHeaders=host&X-Amz-Signature=b9c857335459c67db6913bced5b41dcedcc2d6beefbd1f02e132c0d3896d87ae
```

However internally the hub will take the last compoent of the URL path, `all-drugbank-vocabulary`, as the filename, and because there is no suffix `.zip` in it, the hub will not know how to decompress it.
