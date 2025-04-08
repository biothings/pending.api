# DISEASES
Originally from https://github.com/kevinxin90/DISEASES.git

## To generate KGX files (WIP)

Use the biothings-cli dumper to download files locally.  Files are specified in manifest.json and stored in `.biothings_hub/archive/DISEASES/1.0`
```
biothings-cli dataplugin dump
```

Run the `kgx_export.py` script, which calls `parser.py` and then exports a small number of records. Currently this outputs in JSON lines to `example_output.json`
```
python3 kgx_export.py
```