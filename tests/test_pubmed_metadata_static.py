import importlib.util
from pathlib import Path


STATIC_PATH = Path(__file__).parents[1] / "plugins" / "pubmed_metadata" / "static.py"
STATIC_SPEC = importlib.util.spec_from_file_location("pubmed_metadata_static", STATIC_PATH)
static = importlib.util.module_from_spec(STATIC_SPEC)
assert STATIC_SPEC.loader is not None
STATIC_SPEC.loader.exec_module(static)


def test_pinned_release_has_all_expected_shards():
    assert static.RELEASE == "2026jun30"
    assert static.SHARD_COUNT == 16
    assert static.PUBMED_METADATA_FILES == tuple(
        f"pubmed_metadata_{index:05d}.ndjson.gz" for index in range(16)
    )
    assert static.PUBMED_METADATA_URLS == tuple(
        f"{static.BASE_URL}{filename}" for filename in static.PUBMED_METADATA_FILES
    )
