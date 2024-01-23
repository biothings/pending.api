"""
Custom backend implementation index modification for the PFOCR data access
"""

import logging
from typing import Dict

from biothings.web.query.engine import AsyncESQueryBackend


logger = logging.getLogger(__name__)


class PFOCRBackend(AsyncESQueryBackend):
    """
    Overridden AsyncESQueryBackend implementation

    Inheritance Flow
    PFOCRBackend <pending.api.web.engine.pfocr.PFOCRBackend>
         |
         V
    AsyncESQueryBackend <biothings.web.query.engine.AsyncESQueryBackend>
         |
         V
    ESQueryBackend <biothings.web.query.engine.ESQueryBackend>

    We override the ESQueryBackend.apply_index to select the index we want
    based off the query options

    Examples query syntax
    <url>:<port>/pfocr/query?q=associatedWith.pmc:PMC3521791&<flavor>
    where <flavor> can be {strict, synonyms, all}
    If the flavor isn't supplied then all PFOCR elasticsearch indices
    are used. These indices are set in pending.api.config_web.pfocr
    """

    def adjust_index(self, original_index: str, query: str, **options: Dict) -> str:
        """
        Index modification for selecting the PFOCR flavor index
        """
        query_index = original_index

        strict_flavor = options.get("strict", None)
        synonyms_flavor = options.get("synonyms", None)

        if strict_flavor:
            query_index = self.indices.get("strict", None)
            logger.debug(f"Discovered PFOCR strict option. Changing ES index to {query_index}")
        elif synonyms_flavor:
            query_index = self.indices.get("synonyms", None)
            logger.debug(f"Discovered PFOCR synonyms option. Changing ES index to {query_index}")
        else:
            query_index = self.indices.get("all", None)
            logger.debug(f"Discovered PFOCR all option. Changing ES index to {query_index}")

        return query_index
