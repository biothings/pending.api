from urllib.parse import urlparse

from biothings.web.handlers import BaseAPIHandler

from web.handlers.nodenorm.biolink import BIOLINK_MODEL_VERSION


class NodeNormHealthHandler(BaseAPIHandler):
    """
    Important Endpoints
    * /_cat/nodes
    """

    name = "health"

    async def get(self):

        compendia_url = self.biothings.metadata.biothing_metadata["node"]["src"]["nodenorm"]["url"]
        parsed_compendia_url = urlparse(compendia_url)
        babel_version = parsed_compendia_url.path.split("/")[-2]
        babel_markdown = f"https://github.com/ncatstranslator/Babel/blob/master/releases/{babel_version}.md"
        try:
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
            h_string = ",".join(attributes)
            cat_nodes_response = await self.biothings.elasticsearch.async_client.cat.nodes(format="json", h=h_string)
            nodes_status = {node["name"]: node for node in cat_nodes_response}
            nodes = {"elasticsearch": {"nodes": nodes_status}}
        except Exception as gen_exc:
            status_response = {
                "status": "error",
                "babel_version": babel_version,
                "babel_version_url": babel_markdown,
            }
        else:
            status_response = {
                "status": "running",
                "babel_version": babel_version,
                "babel_version_url": babel_markdown,
                "biolink_model_toolkit_version": BIOLINK_MODEL_VERSION,
                **nodes,
            }

        self.finish(status_response)
