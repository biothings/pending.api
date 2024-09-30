import logging

from biothings.web.handlers import BaseAPIHandler
from biothings.web.handlers.services import StatusHandler


logger = logging.getLogger(__name__)


class StatusDefaultHandler(BaseAPIHandler):
    name = "status"

    async def get(self, *args, **kwargs):
        self.request.uri = "/idisk/status"
        status_handler = StatusHandler(
            self.application, self.request, **kwargs
        )
        await status_handler._execute([])
        self._finished = True  # Ensure the request handling is marked as complete


    async def head(self, *args, **kwargs):
        self.request.uri = "/idisk/status"
        status_handler = StatusHandler(
            self.application, self.request, **kwargs
        )
        await status_handler._execute([])
        self._finished = True  # Ensure the request handling is marked as complete
