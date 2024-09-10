import logging
import os

from git import Repo
from biothings.web.handlers import BaseAPIHandler

logger = logging.getLogger(__name__)

class VersionHandler(BaseAPIHandler):
    name = "version"

    def get_github_commit_hash(self):
        """Retrieve the current GitHub commit hash using gitpython."""
        try:
            # Assuming the .git directory is in the parent folder of this file
            repo_dir = os.path.abspath(os.path.dirname(__file__))
            repo = Repo(repo_dir)
            commit_hash = repo.head.commit.hexsha  # Get the latest commit hash
            return commit_hash
        except Exception as e:
            logger.error(f"Error getting GitHub commit hash: {e}")
            return "Unknown"

    async def get(self, *args, **kwargs):
        version = self.get_github_commit_hash()
        self.write({"version": version})
