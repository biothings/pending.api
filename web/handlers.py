"""
    Dynamic Web Pages
"""

import json
import logging

import tornado.httpclient
import tornado.web
from jinja2 import Environment, FileSystemLoader

log = logging.getLogger("pending")

templateLoader = FileSystemLoader(searchpath='static/html/')
templateEnv = Environment(loader=templateLoader, cache_size=0)


class FrontPageHandler(tornado.web.RequestHandler):

    async def get(self):

        http_client = tornado.httpclient.AsyncHTTPClient()
        try:
            response = await http_client.fetch(
                "https://biothings.ncats.io/api/list")
            apilist = json.loads(response.body)['result']
        except Exception as e:
            log.exception("Error retrieving app list.")
            raise tornado.web.HTTPError(503, reason=str(e))

        index_file = "index.html" # default page
        if self.request.host == "biothings.ncats.io":
            index_file = "ncats-landing.html"

        template = templateEnv.get_template(index_file)
        output = template.render(Context=json.dumps({"List": apilist}))
        self.finish(output)


class ApiViewHandler(tornado.web.RequestHandler):

    def get(self):
        template = templateEnv.get_template("try.html")
        output = template.render()
        self.finish(output)


EXTRA_HANDLERS = [
    (r"/", FrontPageHandler),
    (r"/[^/]+", ApiViewHandler),
]
