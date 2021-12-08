"""
    https://pending.biothings.io/
    https://biothings.ncats.io/
"""

from biothings.web.launcher import main
from web.handlers import EXTRA_HANDLERS

if __name__ == "__main__":
    main(EXTRA_HANDLERS, {"static_path": "static"})
