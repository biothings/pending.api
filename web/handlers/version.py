import logging
import os
import subprocess
from biothings.web.handlers import BaseAPIHandler

logger = logging.getLogger(__name__)

class VersionHandler(BaseAPIHandler):
    name = "version"

    def get_github_commit_hash(self):
        """Retrieve the current GitHub commit hash using git command."""
        try:
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=os.path.dirname(__file__),  # Ensure we're in the correct directory
                universal_newlines=True
            ).strip()
            return commit_hash
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting GitHub commit hash: {e}")
            return "Unknown"

    async def get(self, *args, **kwargs):
        # # Try to read the version from the version.txt file
        # try:
        #     with open("version.txt", "r") as version_file:
        #         version = version_file.read().strip()
        #         self.write(version)
        # except FileNotFoundError:
        #     # Handle the case where version.txt doesn't exist
        #     logger.error("version.txt file not found")
        #     self.set_status(404)
        #     self.write("Version not available")
        version = self.get_github_commit_hash()
        self.write(version)
