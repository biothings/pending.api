import logging

from biothings.web.handlers import BaseAPIHandler


logger = logging.getLogger(__name__)


class ValidConflationsHandler(BaseAPIHandler):
    name = "allowed-conflations"

    async def get(self):
        conflations = ["GeneProtein", "DrugChemical"]
        self.finish(conflations)

    async def head(self):
        conflations = ["GeneProtein", "DrugChemical"]
        self.finish(conflations)
