import logging
from biothings.web.handlers import BaseAPIHandler

logger = logging.getLogger(__name__)

class VersionHandler(BaseAPIHandler):
    name = "version"

    async def get(self, *args, **kwargs):
        # Try to read the version from the version.txt file
        try:
            with open("version.txt", "r") as version_file:
                version = version_file.read().strip()
            self.write(version)
        except FileNotFoundError:
            # Handle the case where version.txt doesn't exist
            logger.error("version.txt file not found")
            self.set_status(404)
            self.write("Version not available")
