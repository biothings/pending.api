from biothings.web.handlers import BaseAPIHandler
from biothings.web.services.namespace import BiothingsNamespace
from tornado.web import HTTPError


class NodeNormStatusHandler(BaseAPIHandler):
    """
    Important Endpoints
    * /_cat/nodes

    """

    name = "status"

    async def get(self):
        try:
            cat_nodes_response = await self.biothings.elasticsearch.async_client.cat.nodes()
            nodes_info_response = await self.biothings.elasticsearch.async_client.nodes.info()
            nodes_stats_response = await self.biothings.elasticsearch.async_client.nodes.stats()
        except Exception as gen_exc:
            network_error = HTTPError(
                detail="Unable to access the elasticsearch index for type information", status_code=500
            )
            raise network_error from gen_exc
        breakpoint()

        status_response = {
            "babel_version": "2025sep1",
            "babel_version_url": "https://github.com/ncatstranslator/Babel/blob/master/releases/2025sep1.md",
        }

        self.finish(status_response)
