import logging
import os
import json

from biothings.web.handlers import BaseAPIHandler
from tornado.web import HTTPError
from tornado.httpclient import AsyncHTTPClient, HTTPError as TornadoHTTPError


logger = logging.getLogger(__name__)


class StatusHandler(BaseAPIHandler):
    name = "status"

    async def get(self, *args, **kwargs):
        http_client = AsyncHTTPClient()
        host = str(os.getenv("ES_HOST", "http://localhost:9200"))
        url_check = f"{host}/pending-rhea/_count"
        logger.info(f"url_check: {url_check}")

        try:
            response = await http_client.fetch(url_check)
            response_data = json.loads(response.body.decode())

            if response.code == 200:
                count = response_data.get('count', 0)

                if count > 0:
                    self.write({"success": True})
                else:
                    logger.error(f"Error fetching _count from Elasticsearch: {response.body.decode()}")
                    raise HTTPError(response.code, f"Error fetching _count: {response.body.decode()}")
            else:
                logger.error(f"Received non-200 response from Elasticsearch _count endpoint: {response.code}")
                raise HTTPError(response.code, f"Error fetching _count: {response.body.decode()}")

        except TornadoHTTPError as e:
            logger.error(f"Error fetching _count from Elasticsearch: {e}")
            raise HTTPError(e.code, f"Error fetching _count: {e.message}")
