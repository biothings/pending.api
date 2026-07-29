"""Elasticsearch mapping for transformed PubMed metadata documents."""

from copy import deepcopy


PUBMED_DATE_FORMAT = "strict_date||strict_year_month||strict_year"
MAX_SORTABLE_TEXT_LENGTH = 8191


def _sortable_text() -> dict:
    return {
        "type": "text",
        "fields": {
            "raw": {
                "type": "keyword",
                "ignore_above": MAX_SORTABLE_TEXT_LENGTH,
            }
        },
    }


PUBMED_METADATA_MAPPING = {
    "pubmed": {
        "properties": {
            "journal": {
                "properties": {
                    "name": _sortable_text(),
                    "abbr": {"type": "keyword"},
                },
            },
            "title": {"type": "text"},
            "vol": {"type": "keyword"},
            "iss": {"type": "keyword"},
            "pub_date": {
                "type": "date",
                "format": PUBMED_DATE_FORMAT,
            },
            "abstract": {"type": "text", "index": False},
        },
    }
}


def get_pubmed_metadata_mapping() -> dict:
    """Return an independent mapping because Hub consumers may mutate it."""
    return deepcopy(PUBMED_METADATA_MAPPING)
