"""
Overridden definitions
"""

from biothings.web.settings.default import APP_LIST


def pending_application_list():
    """
    Override the APP_LIST collection with any pending.api specific
    handlers we wish to utilize

    Current override:
    biothings.web.handlers.MetadataFieldHandler -> web.handlers.metadata.PendingMetadataSourceHandler
    """

    removal_terms = [(r"/{pre}/metadata/?", "biothings.web.handlers.MetadataSourceHandler")]
    for removal_term in removal_terms:
        APP_LIST.remove(removal_term)

    override_terms = [(r"/{pre}/metadata/?", "web.handlers.metadata.PendingMetadataSourceHandler")]
    APP_LIST.extend(override_terms)
    return APP_LIST
