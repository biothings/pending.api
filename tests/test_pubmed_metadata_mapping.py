import importlib.util
from pathlib import Path


MAPPING_PATH = Path(__file__).parents[1] / "plugins" / "pubmed_metadata" / "mapping.py"
MAPPING_SPEC = importlib.util.spec_from_file_location("pubmed_metadata_mapping", MAPPING_PATH)
mapping_module = importlib.util.module_from_spec(MAPPING_SPEC)
assert MAPPING_SPEC.loader is not None  # nosec B101
MAPPING_SPEC.loader.exec_module(mapping_module)


def test_abstract_is_retrieval_only():
    properties = mapping_module.get_pubmed_metadata_mapping()["pubmed"]["properties"]

    assert properties["abstract"] == {"type": "text", "index": False}  # nosec B101


def test_metadata_fields_are_searchable_and_sortable():
    properties = mapping_module.get_pubmed_metadata_mapping()["pubmed"]["properties"]

    assert properties["title"] == {"type": "text"}  # nosec B101
    assert properties["journal"]["properties"]["name"]["fields"]["raw"] == {  # nosec B101
        "type": "keyword",
        "ignore_above": 8191,
    }
    assert properties["journal"]["properties"]["abbr"] == {"type": "keyword"}  # nosec B101
    assert properties["vol"] == {"type": "keyword"}  # nosec B101
    assert properties["iss"] == {"type": "keyword"}  # nosec B101


def test_publication_date_accepts_available_precision():
    pub_date = mapping_module.get_pubmed_metadata_mapping()["pubmed"]["properties"]["pub_date"]

    assert pub_date == {  # nosec B101
        "type": "date",
        "format": "strict_date||strict_year_month||strict_year",
    }
