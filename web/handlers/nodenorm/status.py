from urllib.parse import urlparse

from biothings.web.handlers import BaseAPIHandler
from tornado.web import HTTPError


class NodeNormStatusHandler(BaseAPIHandler):
    """
    Important Endpoints
    * /_cat/nodes
    """

    name = "status"

    async def get(self):
        attributes = [
            "name",
            "cpu",
            "disk.avail",
            "disk.total",
            "disk.used",
            "disk.used_percent",
            "heap.current",
            "heap.max",
            "load_1m",
            "load_5m",
            "load_15m",
            "uptime,version",
        ]
        try:
            h_string = ",".join(attributes)
            cat_nodes_response = await self.biothings.elasticsearch.async_client.cat.nodes(format="json", h=h_string)
            nodes_status = {node["name"]: node for node in cat_nodes_response}
            nodes = {"elasticsearch": {"nodes": nodes_status}}
        except Exception as gen_exc:
            network_error = HTTPError(
                detail="Unable to access the elasticsearch index for type information", status_code=500
            )
            raise network_error from gen_exc
        else:
            compendia_url = self.biothings.metadata.biothing_metadata["node"]["src"]["nodenorm"]["url"]
            parsed_compendia_url = urlparse(compendia_url)
            babel_version = parsed_compendia_url.path.split("/")[-2]
            babel_markdown = f"https://github.com/ncatstranslator/Babel/blob/master/releases/{babel_version}.md"

            status_response = {
                "babel_compendia": compendia_url,
                "babel_version": babel_version,
                "babel_version_url": babel_markdown,
                **nodes,
            }

        self.finish(status_response)
