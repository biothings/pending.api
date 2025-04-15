import logging
import types
from typing import Union

from biothings.web.settings.configs import load_module, ConfigModule, ConfigPackage

from web.settings.override import pending_application_list
from web.settings.validators import PendingWebApiValidator

logger = logging.getLogger(__name__)


class PendingAPIConfigModule(ConfigModule):
    override_mapping = None


    def __init__(self, config=None, parent=None, validators: tuple = (), **kwargs):
        override_terms = self._build_override_lookup()
        super().__init__(config=config, parent=parent, validators=validators, **override_terms)
        self.module = config
        self.validators = validators
        self._valid_webapi = None

    @property
    def valid_webapi(self):
        if self._valid_webapi is None:
            valid_webapi_module_status = False
            for validator in self.validators:
                if isinstance(validator, PendingWebApiValidator):
                    module_api_prefix = getattr(self.module, "API_PREFIX", None)
                    valid_webapi_module_status = module_api_prefix in validator.api_prefixes
            self._valid_webapi = valid_webapi_module_status
        return self._valid_webapi

    @classmethod
    def _build_override_lookup(cls) -> dict:
        """
        With the configuration module (ConfigModule), the __getattr__ method
        has been explicitly defined to lookup attributes in the following order:

        0) override
        1) primary
        2) fallback
        3) default

        In order to provide custom behavior for the pending.api, we can explicitly define mappings
        that take precedence over the default values

        Current Usage:
        We wish to explicitly change the metadata lookup handler to be the pending.api version

        The handler mapping definition is specified in the APP_LIST collection under:
            >>> biothings.web.settings.default

        So if we wish to specify a pending.api version of that we can provide a list of kwargs
        to the constructor when building the ConfigModule to populate the override lookup
        and ensure that the pending.api specific APP_LIST is found before the default one
        stored in the biothings hub

        We make this a class method at the moment because if we have singular PendingAPIConfigModule
        then this will only have to be performed once when we transform the APP_LIST. However, in
        the case of multiple PendingAPIConfigModule in the case we we're running the full hub with
        the config_web package, we don't want to keep transforming the APP_LIST. So we store
        `override_mapping` at the class level rather than the instance level and only call
        `pending_application_list` once per package
        """
        if cls.override_mapping is None:
            cls.override_mapping = {"APP_LIST": pending_application_list()}
        return cls.override_mapping


def load_configuration(config_module: str = None) -> Union[ConfigPackage, PendingAPIConfigModule]:
    """
    Custom loading for the pending.api

    Modified version of the biothings.api configuration
    found in <biothings.web.settings.configs>

    Flow:
    1) Leverages the `load_module` method to transform our
    input config_module to types.ModuleType
    2) Determine if the configuration is a package or not.
    See [PEP366](https://peps.python.org/pep-0366/) for details
    on what that means. For explicit clarity, any python file is
    defined as a `module`. A `package` is collection of python modules.
    This check is verifying if we have singular or plural modules in
    the configuration. The pending.api itself has many configuration
    modules within the config_web package, but we want to ensure we
    can run if only one of them is specified
    """
    if config_module is None:
        config_module = "config"
    config_module = load_module(config_module)

    validators = (PendingWebApiValidator(),)

    if config_module.__package__ == config_module.__name__:
        attributes = [getattr(config_module, attr) for attr in dir(config_module)]
        module_attributes = [attr for attr in attributes if isinstance(attr, types.ModuleType)]

        root_module = PendingAPIConfigModule(config_module)
        package_modules = []
        for module in module_attributes:
            config_module_instance = PendingAPIConfigModule(config=module, parent=config_module, validators=validators)
            if config_module_instance.valid_webapi:
                package_modules.append(config_module_instance)

        configuration_package = ConfigPackage(root_module, package_modules)

        return configuration_package
    elif not config_module.__package__ == config_module.__name__:
        singular_config_module = PendingAPIConfigModule(config=config_module, validators=validators)
        return singular_config_module
