import logging
import types
from typing import Union

from biothings.web.settings.configs import load_module, ConfigModule, ConfigPackage

from web.settings.validators import PendingWebApiValidator

logger = logging.getLogger(__name__)


class PendingAPIConfigModule(ConfigModule):
    def __init__(self, config=None, parent=None, validators: tuple = (), **kwargs):
        super().__init__(config=config, parent=parent, validators=validators)
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
