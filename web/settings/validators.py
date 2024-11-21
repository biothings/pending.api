"""
Validation checkers for the assorted web api's
supported within the pending.api
"""

import logging
import json
import types

from biothings.web.settings import default


logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """
    Used for indicating a semantic error in our configuration
    """


class PendingWebApiValidator:

    def __init__(self):
        self.api_prefixes = set()

    def _get_pending_api_module_state(self, config_module: types.ModuleType) -> dict:
        """
        Checks for module attributes to indicate the
        module status for the pending web-api configuration
        """
        api_prefix = getattr(config_module, "API_PREFIX", None)
        app_prefix = getattr(config_module, "APP_PREFIX", None)
        is_webapi = api_prefix is not None or app_prefix is not None
        deprecation_status = getattr(config_module, "API_DEPRECATED", False)
        webapi_module_state = {
            "api_prefix": api_prefix,
            "app_prefix": app_prefix,
            "webapi_module": is_webapi,
            "deprecation_status": deprecation_status,
        }
        return webapi_module_state

    def validate(self, config_module: types.ModuleType):
        """
        Performs validation to ensure that the module belongs to
        the pending.api config_web and isn't an internal python module
        or third-party module external to pending.api

        > Requires APP_VERSION or APP_PREFIX to create a layer of separation
        for the default biothings routes
        """
        module_state = self._get_pending_api_module_state(config_module)
        if module_state["webapi_module"]:
            if module_state["deprecation_status"]:
                logger.warning(
                    "Module %s with is currently deprecated. Module state:\n%s",
                    config_module,
                    json.dumps(module_state, indent=4),
                )
            self._validate_api_attributes(config_module)
            self._validate_elasticsearch_attributes(config_module)
        else:
            logger.info("Excluding module %s from web-api configuration", config_module)

    def _validate_api_attributes(self, config_module: types.ModuleType) -> None:
        """
        Performs attibute checking on the module to ensure the existence
        of APP_PREFIX or APP_VERSION

        We have both attributes for legacy compability from the biothings.api
        In reality, all of the pending.api web api's should use the API_PREFIX
        so we default to searching for that. We raise an error indicates

        """
        api_prefix = getattr(config_module, "API_PREFIX", None)
        api_version = getattr(config_module, "API_PREFIX", None)

        if api_prefix is not None:
            config_module.APP_PREFIX = config_module.API_PREFIX

        if api_version is not None:
            config_module.APP_VERSION = config_module.API_VERSION

        app_prefix = getattr(config_module, "APP_PREFIX", None)

        if app_prefix is None:
            validation_error_message = (
                "API Configuration Issue: "
                f"module {config_module} requires a valid value for the APP_PREFIX attribute"
            )
            raise ValidationError(validation_error_message)

        if app_prefix in self.api_prefixes:
            validation_error_message = (
                "API Configuration Issue: duplicate APP_PREFIX value %s "
                "found for module %s. Each APP_PREFIX must be unique in "
                "configuration package",
                app_prefix,
                config_module,
            )
            raise ValidationError(validation_error_message)

        if config_module.APP_VERSION is None and config_module.APP_PREFIX is None:
            debug_config_parameters = {
                "api_prefix": api_prefix,
                "api_version": api_version,
                "app_prefix": getattr(config_module, "APP_PREFIX", None),
                "app_version": getattr(config_module, "APP_VERSION", None),
            }
            validation_error_message = (
                "Configuration Issue: module %s requires defining at least "
                "one of the following attributes: [APP_VERSION, APP_PREFIX]\n%s",
                config_module,
                json.dumps(debug_config_parameters, indent=4),
            )
            raise ValidationError(validation_error_message)

        self.api_prefixes.add(app_prefix)

    def _validate_elasticsearch_attributes(self, config_module: types.ModuleType):
        """
        Ensures that the attributes associated with the elasticsearch configuration
        for the webapi for the pending.api are properly configured
        """
        elasticsearch_indices = getattr(config_module, "ES_INDICES", None)
        if not isinstance(elasticsearch_indices, dict):
            validation_error_message = (
                'Elasticsearch Configuration Issue: module %s with attribute "ES_INDICES" '
                'is improperly defined. "ES_INDICES" must be of type dict. '
                "Discovered value | ES_INDICES=%s",
                config_module,
                elasticsearch_indices,
            )
            raise ValidationError(validation_error_message)

        # compatibility settings to convert ES_INDEX/ES_DOC_TYPE settings to ES_INDICES
        elasticsearch_index = getattr(config_module, "ES_INDEX", None)
        if elasticsearch_index is not None:
            if elasticsearch_indices is default.ES_INDICES:
                config_module.ES_INDICES = {}
            else:
                # combine with the user provided value
                config_module.ES_INDICES = dict(elasticsearch_indices)

            # _doc_type can be None if not provided, in this case, ES_INDEX value will be
            # set to "None" key in ES_INDICES as the default index used in the handlers
            elasticsearch_document_type = getattr(config_module, "ES_DOC_TYPE", None)
            config_module.ES_INDICES[elasticsearch_document_type] = config_module.ES_INDEX

        # encountering the following attributes indicate
        # the application is built for a previous biothings sdk version.
        # for intended behavior, upgrade the config module of the application.
        if hasattr(config_module, "ES_SNIFF"):
            elasticsearch_deprecated_attribute_message = (
                "Elasticsearch Configuration Issue: The usage of the %s attribute "
                "with module %s is associated with an older biothings version and is now deprecated. "
                "Please remove the attribute for usage with the current biothings SDK",
                "ES_SNIFF",
                config_module,
            )
            raise ValidationError(elasticsearch_deprecated_attribute_message)

        if hasattr(config_module, "ES_CLIENT_TIMEOUT"):
            elasticsearch_deprecated_attribute_message = (
                "Elasticsearch Configuration Issue: The usage of the %s attribute "
                "with module %s is associated with an older biothings version and is now deprecated. "
                "Please remove the attribute for usage with the current biothings SDK",
                "ES_CLIENT_TIMEOUT",
                config_module,
            )
            raise ValidationError(elasticsearch_deprecated_attribute_message)
