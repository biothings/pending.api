import os
import time
from math import ceil

import requests
from biothings.hub.dataload.dumper import APIDumper
from config import DATA_ARCHIVE_ROOT

try:
    from biothings import config

    logger = config.logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class ClinicalTrialsGovDumper(APIDumper):
    SRC_NAME = "clinicaltrials_gov"
    SRC_ROOT_FOLDER = os.path.join(DATA_ARCHIVE_ROOT, SRC_NAME)

    @staticmethod
    def get_release():
        resp = requests.get("https://clinicaltrials.gov/api/v2/version").json()
        # Removes time of day from UTC timestamp
        release = resp["dataTimestamp"].split("T")[0]
        return release

    @staticmethod
    def get_document():
        for document, page_idx in _load_studies():
            yield f"{page_idx}.ndjson", document


def _get_total_studies():
    """
    Requests the Clinical Trials API to return the total number of studies

    Returns:
            total_studies: the total number of studies in the database
    """

    size = requests.get("https://clinicaltrials.gov/api/v2/stats/size")
    total_studies = size.json()["totalStudies"]

    return total_studies


def _load_studies():
    """
    Queries the Clinical Trials API for all the studies in the db

    Returns:
            aggregated_studies: a list of all the studies aggregated into a single collection
    """

    API_PAGE = "https://clinicaltrials.gov/api/v2/studies"
    PAGE_SIZE = 1000 # Min: 0, Max: 1000
    DOWNLOAD_DELAY = 1 / 3  #  <= 3 Requests per second

    total_studies = _get_total_studies()

    next_page = None

    total_pages = (total_studies + PAGE_SIZE - 1) // PAGE_SIZE  # Calculate total pages

    for page_idx in range(1, total_pages + 1):
        logger.info(f'Processing page #{page_idx} / {total_pages}')
        payload = (
            {"format": "json", "pageSize": "1000", "pageToken": f"{next_page}"}
            if next_page
            else {"format": "json", "pageSize": "1000"}
        )
        data = requests.get(API_PAGE, params=payload, timeout=60.0)
        page = data.json()

        if 'nextPageToken' in page:
            next_page = page['nextPageToken']
        
        yield page, page_idx

        # time.sleep(DOWNLOAD_DELAY)
