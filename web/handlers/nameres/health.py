from urllib.parse import urlparse

from biothings.web.handlers import BaseAPIHandler

from web.handlers.nameres.biolink import BIOLINK_MODEL_VERSION


class NameResolutionHealthHandler(BaseAPIHandler):
    """
    Important Endpoints
    * /_cat/nodes
    * /{index}/stats
    """

    name = "health"

    async def get(self):

        compendia_url = self.biothings.metadata.biothing_metadata["node"]["src"]["nodenorm"]["url"]
        parsed_compendia_url = urlparse(compendia_url)
        babel_version = parsed_compendia_url.path.split("/")[-2]
        babel_markdown = f"https://github.com/ncatstranslator/Babel/blob/master/releases/{babel_version}.md"

        try:
            index_name = self.biothings.elasticsearch.metadata.indices["node"]
            index_stats_response = await self.biothings.elasticsearch.async_client.indices.stats(
                index=index_name, metrics=["docs", "segments"]
            )

            index_statistics = {
                "numDocs": index_stats_response["indices"][index_name]["docs"].get("count", ""),
                "deletedDocs": index_stats_response["indices"][index_name]["docs"].get("deleted", ""),
                "segmentCount": index_stats_response["indices"][index_name]["segments"].get("count", ""),
                "size": f'{index_stats_response["indices"][index_name]["docs"].get("total_size_in_bytes", "") / 1**9} GB',
            }

        except Exception:
            status_response = {
                "status": "error",
                "babel_version": babel_version,
                "babel_version_url": babel_markdown,
            }
        else:
            status_response = {
                "status": "ok",
                "message": "Reporting results from primary index.",
                "babel_version": babel_version,
                "babel_version_url": babel_version_url,
                "biolink_model_toolkit_version": BIOLINK_MODEL_VERSION,
                **index_statistics,
            }

        self.finish(status_response)
