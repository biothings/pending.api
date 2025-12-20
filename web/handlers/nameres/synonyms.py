"""
Handler for the synonyms endpoint for nameres
"""

import logging

from biothings.web.handlers import BaseAPIHandler
from tornado.web import HTTPError


logger = logging.getLogger(__name__)


class NameResolutionSynonymsHandler(BaseAPIHandler):
    """
    Handles looking up synonyms based off a particular CURIE.

    preferred CURIE normalization is handled via NodeNorm
    """

    name = "synonyms"

    async def get(self):
        try:
            preferred_curies = self.get_arguments("preferred_curies")
            if len(preferred_curies) == 0:
                raise HTTPError(
                    detail="Missing preferred_curies, there must be at least one CURIE to lookup", status_code=400
                )
            synonym_response = await self.synonyms_lookup(preferred_curies)
            self.finish(synonym_response)
        except Exception as gen_exc:
            raise HTTPError(detail="Error occurred during processing.", status_code=500)

    async def post(self):
        try:
            preferred_curies = self.args_json.get("preferred_curies", [])
            if len(preferred_curies) == 0:
                raise HTTPError(
                    detail="Missing curie argument, there must be at least one curie to normalize", status_code=400
                )
            synonym_response = await self.synonyms_lookup(preferred_curies)
            self.finish(synonym_response)
        except Exception as gen_exc:
            raise HTTPError(detail="Error occurred during processing.", status_code=500)

    async def synonyms_lookup(self, curies: list[str]) -> dict[str, dict]:
        """
        Returns a list of synonyms for a particular CURIE.

        """
        curie_terms_query = {"bool": {"filter": [{"terms": {"identifiers.i": curies}}]}}
        index = self.biothings.elasticsearch.metadata.indices["node"]
        term_search_result = await self.biothings.elasticsearch.async_client.search(
            query=curie_terms_query, index=index, size=len(curies)
        )

        output = {curie: {} for curie in curies}
        for result in term_search_result.body["hits"]["hits"]:
            output[result["curie"]] = result
        return output
