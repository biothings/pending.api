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
            # Assuming the .git directory is located in the root of the project
            repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))  # Adjust the path to reach the repo root
            logger.info(f"Repository directory: {repo_dir}")

            # Initialize the Repo object
            repo = Repo(repo_dir)

            if repo.bare:
                logger.error(f"Git repository not found in directory: {repo_dir}")
                return "Unknown"

            commit_hash = repo.head.commit.hexsha  # Get the latest commit hash
            return commit_hash
        except Exception as e:
            logger.error(f"Error getting GitHub commit hash: {e}")
            return "Unknown"

    async def get(self, *args, **kwargs):
        version = self.get_github_commit_hash()
        self.write({"version": version})
