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


__all__ = [
    "ClinicalTrialsGovDumper",
]


class ClinicalTrialsGovDumper(APIDumper):
    SRC_NAME = "clinicaltrials_gov"
    SRC_ROOT_FOLDER = os.path.join(DATA_ARCHIVE_ROOT, SRC_NAME)

    @staticmethod
    def get_release():
        resp = requests.get("https://clinicaltrials.gov/api/v2/version").json()
        # Removes time of day from UTC timestamp
        release = resp["dataTimeStamp"].split("T")[0]
        return release

    @staticmethod
    def get_document():
        for document in _load_studies():
            yield "clinicaltrials_gov.ndjson", document


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

    total_studies = _get_total_studies()

    aggregated_studies = []
    nextPage = None

    request_delay = 1 / 3  #  <= 3 Requests per second

    for _ in range(ceil(total_studies / 1000)):
        payload = (
            {"format": "json", "pageSize": "1000", "pageToken": f"{nextPage}"}
            if nextPage
            else {"format": "json", "pageSize": "1000"}
        )
        data = requests.get("https://clinicaltrials.gov/api/v2/studies", params=payload)
        studies = data.json()

        aggregated_studies.extend(studies["studies"])

        # The last page does not have a nextPageToken field
        if "nextPageToken" not in studies:
            break

        nextPage = studies["nextPageToken"]

        time.sleep(request_delay)

    return aggregated_studies
