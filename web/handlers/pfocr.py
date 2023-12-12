"""
Web handler for routing the data requests for the PFOCR data
"""

import dataclasses
from typing import Dict

from elasticsearch_dsl import Q, Search

from biothings.web.handlers import BaseAPIHandler


@dataclasses.dataclass(init=False, repr=True, order=False, unsafe_hash=False, frozen=True)
class PFOCRFlavor:
    """
    Enumeration class for defining the PFOCR flavor keywords
    """

    STRICT: str = "pfocr_strict"
    SYNONYMS: str = "pfocr_synonyms"
    ALL: str = "pfocr_all"


class PFOCR_Handler(BaseAPIHandler):
    """
    Handler for routing the API query based off the PFOCR "flavor"

    supports three different flavors"
    > strict
    > synonyms
    > all
    """

    name = "pfocr"
    kwargs = dict(BaseAPIHandler.kwargs)
    kwargs["GET"] = {
        "name": {"type": str, "default": None},
        "size": {"type": int, "default": 0},
        "flavor": {"type": str, "default": PFOCRFlavor.STRICT},
    }
    timeout = 120
    size = 0

    async def get(self):
        parameters = {
            "query_str": self.args.name if self.args.name else None,
            "size": self.args.size if self.args.size else 0,
            "flavor": self.args.flavor if self.args.flavor else PFOCRFlavor.STRICT,
        }
        query = self.format_query(parameters)
        if parameters["flavor"] == PFOCRFlavor.ALL:
            query_resp = await self.query_pfocr_flavor_all(query)
        elif parameters["flavor"] == PFOCRFlavor.STRICT:
            query_resp = await self.query_pfocr_flavor_strict(query)
        elif parameters["flavor"] == PFOCRFlavor.SYNONYMS:
            query_resp = await self.query_pfocr_flavor_synonyms(query)

        resp = {"success": True, "results": query_resp}
        return resp

    def format_query(self, parameters: Dict) -> Dict:
        search_instance = Search()
        query_instance = Q("wildcard")
        search_query = search_instance.query(query_instance)
        query_mapping = search_query.to_dict()
        return query_mapping

    async def query_pfocr_flavor_all(self, query):
        query["track_total_hits"] = True
        response = await self.biothings.elasticsearch.async_client.search(
            index=self.biothings.config.pfocr.PFOCR_FLAVOR_ALL,
            body=query,
            request_timeout=self.timeout,
        )
        return response

    async def query_pfocr_flavor_synonyms(self, query):
        query["track_total_hits"] = True
        response = await self.biothings.elasticsearch.async_client.search(
            index=self.biothings.config.genomics.PFOCR_FLAVOR_SYNONYMS,
            body=query,
            size=self.size,
            request_timeout=self.timeout,
        )
        return response

    async def query_pfocr_flavor_strict(self, query):
        query["track_total_hits"] = True
        response = await self.biothings.elasticsearch.async_client.search(
            index=self.biothings.config.genomics.PFOCR_FLAVOR_STRICT,
            body=query,
            size=self.size,
            request_timeout=self.timeout,
        )
        return response
