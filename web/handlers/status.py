import logging

from biothings.web.handlers import BaseAPIHandler
from biothings.web.handlers.services import StatusHandler


logger = logging.getLogger(__name__)


class StatusDefaultHandler(BaseAPIHandler):
    name = "status"

    def set_default_headers(self):
        """Set headers to prevent caching."""
        self.set_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.set_header("Pragma", "no-cache")

    async def get(self, *args, **kwargs):
        self.set_default_headers()
        self.request.uri = "/rhea/status"
        status_handler = StatusHandler(
            self.application, self.request, **kwargs
        )
        status_handler._transforms = self._transforms  # Copy transforms from current handler
        await status_handler.get()

    async def head(self, *args, **kwargs):
        self.set_default_headers()
        self.request.uri = "/rhea/status"
        status_handler = StatusHandler(
            self.application, self.request, **kwargs
        )
        status_handler._transforms = self._transforms  # Copy transforms from current handler
        await status_handler.head()
