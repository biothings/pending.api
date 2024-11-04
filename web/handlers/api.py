"""
Handlers for metrics related to the pending webapi's
"""

import logging

from biothings.web.handlers import BaseAPIHandler
from web.application import PendingAPI

logger = logging.getLogger(__name__)


class ApiListHandler(BaseAPIHandler):
    name = "api-list"

    async def get(self):
        application_handlers = self.application.biothings.handlers
        api_endpoints = set()
        for endpoint, handler_object in application_handlers.items():
            if isinstance(handler_object, PendingAPI):
                api_endpoints.add(endpoint)
        self.write(sorted(api_endpoints))
