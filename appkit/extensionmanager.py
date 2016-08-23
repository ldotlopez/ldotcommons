# -*- encoding: utf-8 -*-

import importlib
import re
import warnings


from appkit import extension
from appkit import types


class PluginNotLoadedError(Exception):
    pass


class PluginWithoutExtensionsError(Exception):
    pass


class ExtensionManager:
    def __init__(self, name, logger=None):
        name = name.replace('-', '_')
        if not re.search(r'^[a-z_][a-z0-9_]*$', name, re.IGNORECASE):
            msg = "name must match '^[a-z_][a-z0-9_]*$'"
            raise ValueError(msg)

        if not logger:
            msg = "{clsname}: No logger configured, messages will be discarted"
            msg = msg.format(clsname=self.__class__.__name__)
            warnings.warn(msg)

            logger = types.Null()

        self.__name__ = name
        self._logger = logger
        self._registry = {}

    def load_plugin(self, plugin):
        fullplugin = self.__name__ + ".plugins." + plugin.replace('-', '_')
        try:
            m = importlib.import_module(fullplugin)
        except ImportError as e:
            msg = "Unable to load plugin {pluginname} ({module}): {message}"
            msg = msg.format(
                pluginname=plugin,
                module=fullplugin,
                message=str(e)
            )
            raise PluginNotLoadedError(msg)

        try:
            extensions_attr = '__{}_extensions__'.format(self.__name__)
            extensions = getattr(m, extensions_attr)
        except AttributeError:
            msg = "Missing attribute {extensions_attr}"
            msg = msg.format(extensions_attr=extensions_attr)
            raise PluginWithoutExtensionsError(msg)

        for ext in extensions:
            self.register_extension_class(ext)

    def register_extension_class(self, cls):
        # Check base type
        if not issubclass(cls, extension.Extension):
            msg = ("Class {cls} is not a valid extension "
                   "(must a subclass of appkit.extension.Extension)")
            msg = msg.format(cls=cls.__name__)
            raise TypeError(msg)

        # Check for mandatory __extension_name__' attr
        if not hasattr(cls, '__extension_name__'):
            msg = ("Class {cls} is not a valid extension "
                   "(must define a __extension_name__' attribute)")
            msg = msg.format(cls=cls.__name__)
            raise TypeError(msg)

        if cls.__extension_name__ in self._registry:
            msg = ("Class {cls} can't be registered, name already registered "
                   "by {other}")
            msg = msg.format(
                cls=cls.__name__,
                other=self._registry[cls.__extension_name__].__name__)
            raise ValueError(msg)

        self._registry[cls.__extension_name__] = cls

        # Support for multiple extensions sharing the same name
        #
        # Check for conflicts
        # keys = set([(basecls, cls.__extension_name__)
        #            for basecls in cls.__bases__])
        # conflicts = set(self._registry).intersection(keys)
        # if conflicts:
        #     msg = ("Class {cls} can't be registered, there are conflicts: "
        #            "{conflicts}")
        #     msg = msg.format(cls=cls.__name__, conflicts=repr(conflicts))
        #     raise ValueError(msg)

        # self._registry.update({
        #     k: cls for k in keys
        # })

    def get_extension_class(self, name):
        return self._registry[name]

        # if issubclass(cls, extension.Service):
        #     if name in self._services:
        #         msg = ("Service '{name}' already registered by "
        #                "'{cls}'")
        #         msg = msg.format(
        #             name=name,
        #             cls=type(self._services[name]))
        #         self.logger.critical(msg)
        #     else:
        #         try:
        #             self._services[cls] = cls(self)
        #         except arroyo.exc.PluginArgumentError as e:
        #             self.logger.critical(str(e))

    def get_extension(self, name, *args, **kwargs):
        return self.get_extension_class(name)(*args, **kwargs)

    def get_implementations(self, cls):
        return [x for x in self._registry.values()
                if issubclass(x, cls)]
