import logging
import pathlib
import git

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

            if repo.bare:
                # Get the absolute path to the repository root
                repo_dir = repo.working_tree_dir
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
