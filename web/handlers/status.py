import logging
import json

from biothings.web.handlers import BaseAPIHandler
from tornado.httpclient import AsyncHTTPClient, HTTPError


logger = logging.getLogger(__name__)


class StatusHandler(BaseAPIHandler):
    name = "status"

    # async def get(self, *args, **kwargs):
    #     self.redirect("/rhea/status")

    # async def head(self, *args, **kwargs):
    #     self.redirect("/rhea/status")

    def set_default_headers(self):
        """Set headers to prevent caching."""
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Pragma", "no-cache")

    async def get(self, *args, **kwargs):
        self.set_default_headers()
        http_client = AsyncHTTPClient()
        try:
            response = await http_client.fetch(self.request.protocol + "://" + self.request.host + "/rhea/status", method="GET")
            if response.code == 200:
                data = json.loads(response.body)
                self.set_status(response.code)
                self.write(data)
            else:
                self.set_status(500)
                self.write({
                    "status": "Unhealthy",
                    "error": f"Upstream returned status {response.code}"
                })
        except HTTPError as e:
            logging.error(f"Failed to get status: {e}")
            self.set_status(500)
            self.write({
                "status": "Unhealthy",
                "error": "Failed to retrieve upstream status"
            })

    async def head(self, *args, **kwargs):
        self.set_default_headers()
        http_client = AsyncHTTPClient()
        try:
            response = await http_client.fetch(self.request.protocol + "://" + self.request.host + "/rhea/status", method="HEAD")
            if response.code == 200:
                self.set_status(200)
            else:
                self.set_status(500)
        except HTTPError as e:
            logging.error(f"Failed to get head status: {e}")
            self.set_status(500)
