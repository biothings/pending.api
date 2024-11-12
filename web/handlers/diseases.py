from biothings.web.handlers import BaseAPIHandler


class DiseasesHandler(BaseAPIHandler):
    name = "diseases"

    async def get(self, *args, **kwargs):
        self.redirect("/diseases", permanent=True)

    async def head(self, *args, **kwargs):
        self.redirect("/diseases", permanent=True)
