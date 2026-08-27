import gzip
import importlib
import json
import sys
import types
from pathlib import Path

import pytest


@pytest.fixture
def uploader_module(monkeypatch, tmp_path):
    biothings = types.ModuleType("biothings")
    biothings.config = types.SimpleNamespace(DATA_ARCHIVE_ROOT=str(tmp_path / "archive"))
    hub = types.ModuleType("biothings.hub")
    dataload = types.ModuleType("biothings.hub.dataload")
    dumper = types.ModuleType("biothings.hub.dataload.dumper")
    uploader = types.ModuleType("biothings.hub.dataload.uploader")
    biothings.__path__ = []
    hub.__path__ = []
    dataload.__path__ = []

    class LastModifiedHTTPDumper:
        pass

    class ParallelizedSourceUploader:
        pass

    dumper.LastModifiedHTTPDumper = LastModifiedHTTPDumper
    uploader.ParallelizedSourceUploader = ParallelizedSourceUploader
    biothings.hub = hub
    hub.dataload = dataload
    dataload.dumper = dumper
    dataload.uploader = uploader
    modules = {
        "biothings": biothings,
        "biothings.hub": hub,
        "biothings.hub.dataload": dataload,
        "biothings.hub.dataload.dumper": dumper,
        "biothings.hub.dataload.uploader": uploader,
    }
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    original_plugin_modules = {
        name: module
        for name, module in tuple(sys.modules.items())
        if name == "plugins.pubmed_metadata" or name.startswith("plugins.pubmed_metadata.")
    }
    for name in original_plugin_modules:
        sys.modules.pop(name)

    yield importlib.import_module("plugins.pubmed_metadata.uploader")

    for name in tuple(sys.modules):
        if name == "plugins.pubmed_metadata" or name.startswith("plugins.pubmed_metadata."):
            sys.modules.pop(name)
    sys.modules.update(original_plugin_modules)


def create_shards(data_folder: Path, filenames: tuple[str, ...]) -> None:
    for filename in filenames:
        data_folder.joinpath(filename).touch()


def write_record(path: Path, pubmed_id: str) -> None:
    record = {
        "id": pubmed_id,
        "journal_name": "Journal of Examples",
        "journal_abbrev": "J Ex",
        "article_title": "A useful example",
        "volume": "12",
        "issue": "3",
        "pub_year": "2026",
        "pub_month": "Jun",
        "pub_day": "30",
        "abstract": "An abstract with Unicode: β.",
    }
    with gzip.open(path, "wt", encoding="utf-8", newline="") as output_file:
        output_file.write(json.dumps(record) + "\n")


def test_jobs_partition_shards_across_four_workers(tmp_path, uploader_module):
    filenames = uploader_module.PUBMED_METADATA_FILES
    create_shards(tmp_path, filenames)

    uploader = uploader_module.PubMedMetadataUploader.__new__(
        uploader_module.PubMedMetadataUploader
    )
    uploader.data_folder = str(tmp_path)

    jobs = uploader.jobs()

    assert len(jobs) == 4  # nosec B101
    assert [len(job[0]) for job in jobs] == [4, 4, 4, 4]  # nosec B101
    assert jobs[0][0] == tuple(  # nosec B101
        str(tmp_path / filename) for filename in filenames[::4]
    )
    assert sorted(path for job in jobs for path in job[0]) == sorted(  # nosec B101
        str(tmp_path / filename) for filename in filenames
    )


def test_jobs_require_every_shard(tmp_path, uploader_module):
    filenames = uploader_module.PUBMED_METADATA_FILES
    create_shards(tmp_path, filenames[:-1])

    uploader = uploader_module.PubMedMetadataUploader.__new__(
        uploader_module.PubMedMetadataUploader
    )
    uploader.data_folder = str(tmp_path)

    with pytest.raises(FileNotFoundError, match=filenames[-1]):
        uploader.jobs()


def test_load_data_streams_every_shard_in_a_worker_group(tmp_path, uploader_module):
    first_shard = tmp_path / "pubmed_metadata_00000.ndjson.gz"
    second_shard = tmp_path / "pubmed_metadata_00004.ndjson.gz"
    write_record(first_shard, "PMID:12345678")
    write_record(second_shard, "PMID:87654321")

    uploader = uploader_module.PubMedMetadataUploader.__new__(
        uploader_module.PubMedMetadataUploader
    )
    documents = list(uploader.load_data((str(first_shard), str(second_shard))))

    assert [document["_id"] for document in documents] == [  # nosec B101
        "PMID:12345678",
        "PMID:87654321",
    ]
    assert documents[0]["pubmed"]["pub_date"] == "2026-06-30"  # nosec B101
