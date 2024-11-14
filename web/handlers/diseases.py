from biothings.web.handlers import BaseAPIHandler


class DiseasesHandler(BaseAPIHandler):
    name = "diseases"

    def prepare(self):
        current_path = self.request.path
        if current_path.startswith("/DISEASES"):
            new_path = current_path.replace("/DISEASES", "/diseases", 1)
            if self.request.query:
                new_path += "?" + self.request.query
            self.redirect(new_path, status=308)
