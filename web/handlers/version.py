import logging
import os
import pathlib
import git

from git import Repo
from biothings.web.handlers import BaseAPIHandler

logger = logging.getLogger(__name__)

class VersionHandler(BaseAPIHandler):
    name = "version"

    def get_github_commit_hash(self):
        """Retrieve the current GitHub commit hash using gitpython."""
        try:
            # Resolve the absolute path to the current file
            file_path = pathlib.Path(__file__).resolve()

            # Use git.Repo to find the root of the repository
            repo = git.Repo(file_path, search_parent_directories=True)

            # Get the absolute path to the repository root
            repo_dir = repo.working_tree_dir

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
