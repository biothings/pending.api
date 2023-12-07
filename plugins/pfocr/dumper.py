"""
Methods for pulling down the PFOCR data

Currently the data is hosted on a dropbox instance across 3 files
pfocr:all -> https://www.dropbox.com/scl/fi/yw4ijp0gkm17muju3awgs/bte_chemicals_diseases_genes_all.ndjson?rlkey=ntqdd32uybdi3b514dvc36tmn&dl=0
pfocr:synonyms -> https://www.dropbox.com/scl/fi/xlyjpqj9dw79jp1y1lwbr/bte_chemicals_diseases_genes_synonyms.ndjson?rlkey=o2x0lhrab10svdou1lrl6jv4j&dl=0
pfocr:strict -> https://www.dropbox.com/scl/fi/igoqupv3qi138vm9scfxs/bte_chemicals_diseases_genes_strict.ndjson?rlkey=50icp9qn4jqjr5l8ubiaknulz&dl=0
"""

from pathlib import Path

import requests


def get_dropbox_file(url, filename, chunk_size=None, timeout=None):
    """
    Leverages the requests module to pull down the specific PFOCR files
    from dropbox leveraging a specific technique using the wget headers

    Reference:
    https://stackoverflow.com/a/46005478
    """
    if chunk_size is None:
        chunk_size = 8192

    if timeout is None:
        timeout = 60

    headers = {"user-agent": "Wget/1.16 (linux-gnu)"}
    with requests.get(url, stream=True, headers=headers, timeout=timeout) as request_object:
        with open(filename, "wb") as file_handle:
            for chunk in request_object.iter_content(chunk_size=chunk_size):
                if chunk is not None:
                    file_handle.write(chunk)
    return Path(filename).absolute().resolve()


def download_pool():
    """
    Pool for collecting and executing groups of download actions
    """
    download_mapping = {
        "pfocr_all": "https://www.dropbox.com/scl/fi/yw4ijp0gkm17muju3awgs/bte_chemicals_diseases_genes_all.ndjson?rlkey=ntqdd32uybdi3b514dvc36tmn&dl=0",
        "pfocr_synonyms": "https://www.dropbox.com/scl/fi/xlyjpqj9dw79jp1y1lwbr/bte_chemicals_diseases_genes_synonyms.ndjson?rlkey=o2x0lhrab10svdou1lrl6jv4j&dl=0",
        "procr_strict": "https://www.dropbox.com/scl/fi/igoqupv3qi138vm9scfxs/bte_chemicals_diseases_genes_strict.ndjson?rlkey=50icp9qn4jqjr5l8ubiaknulz&dl=0",
    }
    downloaded_files = []
    for file_stem, file_url in download_mapping.items():
        filename = f"{file_stem}.ndjson"
        downloaded_file_path = get_dropbox_file(file_url, filename)
        downloaded_files.append(downloaded_file_path)


if __name__ == "__main__":
    download_pool()
