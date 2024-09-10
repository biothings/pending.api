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
            # Ensure an absolute path to avoid directory issues
            repo_dir = os.path.abspath(os.path.dirname(__file__))
            
            # Run the git command to get the commit hash
            commit_hash = subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_dir,  # Ensure we're in the correct directory
                universal_newlines=True
            ).strip()

            return commit_hash
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting GitHub commit hash: {e}")
            return "Unknown"
        except FileNotFoundError:
            logger.error("Git command not found")
            return "Git not available"
        except Exception as e:
            logger.error(f"Unexpected error getting GitHub commit hash: {e}")
            return "Unknown"

    async def get(self, *args, **kwargs):
        version = self.get_github_commit_hash()
        self.write({"version": version})
