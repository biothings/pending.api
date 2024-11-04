"""
Handlers for metrics related to the pending webapi's
"""

import logging
import pathlib
import git

from biothings.web.handlers import BaseAPIHandler

logger = logging.getLogger(__name__)


class ApiListHandler(BaseAPIHandler):
    name = "api-list"

    async def get(self, *args, **kwargs):
        breakpoint()
        version = None
        self.write({"version": version})
