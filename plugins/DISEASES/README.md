# DISEASES
Originally from https://github.com/kevinxin90/DISEASES.git

## To generate KGX files (WIP)

Use the biothings-cli dumper to download files locally.  Files are specified in manifest.json and stored in `.biothings_hub/archive/DISEASES/1.0`
```
biothings-cli dataplugin dump
```

Run the export script. Currently this outputs in JSON lines to `example_output.json`
```
python3 kgx_export.py
```