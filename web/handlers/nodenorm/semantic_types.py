from biothings.web.handlers import BaseAPIHandler
from tornado.web import HTTPError

from web.handlers.nodenorm.biolink import load_biolink_model_toolkit


class SemanticTypeHandler(BaseAPIHandler):
    """
    Mirror implementation to the renci implementation found at
    https://nodenormalization-sri.renci.org/docs

    We intend to mirror the /get_semantic_types endpoint
    """

    name = "semantic_types"

    async def get(self) -> dict:
        type_aggregation = {"unique_types": {"terms": {"field": "type", "size": 100}}}
        source_fields = ["type"]
        try:
            index = self.biothings.elasticsearch.metadata.indices["node"]
            type_aggregation_result = await self.biothings.elasticsearch.async_client.search(
                aggregations=type_aggregation, index=index, size=0, source_includes=source_fields
            )
        except Exception as gen_exc:
            network_error = HTTPError(
                detail="Unable to access the elasticsearch index for type information", status_code=500
            )
            raise network_error from gen_exc

        semantic_types = set()
        toolkit = load_biolink_model_toolkit()
        for bucket in type_aggregation_result.body["aggregations"]["unique_types"]["buckets"]:
            biolink_type = bucket["key"]
            semantic_types.add(biolink_type)
            for ancestor in toolkit.get_ancestors(biolink_type):
                semantic_types.add(toolkit.get_element(ancestor)["class_uri"].lower())

        semantic_type_response = {"semantic_types": {"types": list(semantic_types)}}
        self.finish(semantic_type_response)
