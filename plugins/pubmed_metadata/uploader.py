"""Uploader for the RENCI PubMed metadata export."""

from pathlib import Path

from biothings.hub.dataload.uploader import ParallelizedSourceUploader

from .mapping import get_pubmed_metadata_mapping
from .parser import iter_pubmed_metadata_documents
from .static import BASE_URL, NLM_TERMS_URL, PUBMED2DB_URL, PUBMED_METADATA_FILES


class PubMedMetadataUploader(ParallelizedSourceUploader):
    """Stream each upstream shard into one source collection."""

    name = "pubmed_metadata"
    MAX_PARALLEL_UPLOAD = 4
    keep_archive = 1
    __metadata__ = {
        "src_meta": {
            "url": BASE_URL,
            "license": "NLM PubMed Terms and Conditions",
            "license_url": NLM_TERMS_URL,
            "description": (
                "PubMed citation metadata exported for Translator by "
                f"{PUBMED2DB_URL}"
            ),
        }
    }

    def jobs(self) -> list[tuple[tuple[str, ...]]]:
        data_folder = Path(self.data_folder)
        shard_paths = [data_folder / filename for filename in PUBMED_METADATA_FILES]
        missing_paths = [path.name for path in shard_paths if not path.is_file()]
        if missing_paths:
            raise FileNotFoundError(
                "PubMed metadata upload requires all 16 shards; missing: "
                + ", ".join(missing_paths)
            )

        # pending.api still uses BioThings Hub 0.12.x, whose parallel uploader
        # does not enforce MAX_PARALLEL_UPLOAD. Partitioning the shards into
        # four jobs preserves the source's intended concurrency on both the
        # 0.12.x and 1.x Hub implementations.
        shard_groups = [
            tuple(str(path) for path in shard_paths[group_index:: self.MAX_PARALLEL_UPLOAD])
            for group_index in range(self.MAX_PARALLEL_UPLOAD)
        ]
        return [(group,) for group in shard_groups]

    def load_data(self, data_paths: tuple[str, ...]):
        for data_path in data_paths:
            yield from iter_pubmed_metadata_documents(data_path)

    @classmethod
    def get_mapping(cls) -> dict:
        return get_pubmed_metadata_mapping()
