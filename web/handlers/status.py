import logging
import os

from biothings.web.handlers import BaseAPIHandler
from tornado.web import HTTPError
from tornado.httpclient import AsyncHTTPClient, HTTPError as TornadoHTTPError


logger = logging.getLogger(__name__)


class StatusHandler(BaseAPIHandler):
    name = "status"

    async def get(self, *args, **kwargs):
        http_client = AsyncHTTPClient()

        # Get application host and port
        # host, port = self.request.host.split(':')
        port = os.getenv("APP_PORT", "8000")

        try:
            # Make an asynchronous GET request to the /rhea/status endpoint
            response = await http_client.fetch(f"http://127.0.0.1:{port}/rhea/status")

            # Check if the response status code is 200
            if response.code == 200:
                # Return success if the response is OK
                self.write({"success": True})
            else:
                # Raise an error if the response is not 200
                logger.error(f"Received non-200 response from /rhea/status: {response.code}")
                raise HTTPError(response.code, f"Error fetching /rhea/status: {response.body.decode()}")

        except TornadoHTTPError as e:
            # Log and raise the error if the request failed
            logger.error(f"Error fetching /rhea/status: {e}")
            raise HTTPError(e.code, f"Error fetching /rhea/status: {e.message}")
