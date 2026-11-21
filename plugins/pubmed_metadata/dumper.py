"""Dumper for the RENCI PubMed metadata export."""

from pathlib import Path

from biothings import config
from biothings.hub.dataload.dumper import LastModifiedHTTPDumper

from .static import PUBMED_METADATA_URLS, RELEASE


class PubMedMetadataDumper(LastModifiedHTTPDumper):
    """Download the pinned PubMed metadata snapshot in bounded parallelism."""

    SRC_NAME = "pubmed_metadata"
    SRC_ROOT_FOLDER = Path(config.DATA_ARCHIVE_ROOT) / SRC_NAME
    SRC_URLS = list(PUBMED_METADATA_URLS)

    ARCHIVE = True
    AUTO_UPLOAD = True
    MAX_PARALLEL_DUMP = 4
    RESOLVE_FILENAME = False
    SCHEDULE = None

    def set_release(self) -> None:
        """Use the date encoded in the pinned upstream directory."""
        self.release = RELEASE
