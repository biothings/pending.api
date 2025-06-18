"""
Provides an override for the metadata handlers
in the biothings SDK for custom pending.api behavior

MetadataSourceHandler -> PendingMetadataSourceHandler
"""

from biothings.web.handlers.query import MetadataSourceHandler


class PendingMetadataSourceHandler(MetadataSourceHandler):
    """
    Provides custom metadata for the pending.api sources.

    At the moment provides the SMARTAPI identifier for sources
    where the identifer exists

    We leverage this through the `extras` command that provides
    an injection point for modifying the data
    """

    def extras(self, _meta: dict) -> dict:
        """
        Current metadata additions:
            >>> inject the SMARTAPI identifier
        """
        config = self.biothings.config

        if hasattr(config, 'SMARTAPI_ID'):
            smartapi_mapping = {
                "id": getattr(config, "SMARTAPI_ID", "")
            }
            _meta["smartapi"] = smartapi_mapping

        return _meta
