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
        self.redirect("/rhea/status")
