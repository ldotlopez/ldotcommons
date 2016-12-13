# -*- encoding: utf-8 -*-


import importlib
import re
import warnings


from appkit import (
    exceptions,
    types
)
from appkit.extension import Extension


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

        # Big warning: We cant preregister Extension as extension_point
        # because we can't have parents and childrens registered at the same time.
        # DON'T uncomment the next line
        #
        # self.register_extension_point(Extension)

    def register_extension_point(self, basecls):
        def check_subclass(a, b):
            return issubclass(a, b) or issubclass(b, a)

        if hasattr(basecls, '__extension_name__'):
            msg = "Attempt to register an extension as extension point"
            raise TypeError(msg)

        if basecls in self._registry:
            msg = "Extension point {clsname} already registered"
            msg = msg.format(clsname=basecls.__name__)
            raise exceptions.ExtensionManagerError(msg)

        for ext_point in self._registry:
            if check_subclass(basecls, ext_point):
                msg = "Extension point {cls1} is a subclass of {cls2} (or viceversa)"
                msg = msg.format(cls1=basecls.__name__, cls2=ext_point.__name__)
                raise exceptions.ExtensionManagerError(msg)

        self._registry[basecls] = {}

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
        if not issubclass(cls, Extension):
            msg = ("Class {cls} is not a valid extension "
                   "(must a subclass of appkit.app.Extension)")
            msg = msg.format(cls=cls.__module__+'.'+cls.__name__)
            raise TypeError(msg)

        # Check for mandatory __extension_name__' attr
        if not hasattr(cls, '__extension_name__'):
            msg = ("Class {cls} is not a valid extension "
                   "(must define a __extension_name__' attribute)")
            msg = msg.format(cls=cls.__module__+'.'+cls.__name__)
            raise TypeError(msg)

        # Search for matching extension point
        extension_point = None
        for ext_point in self._registry:
            if issubclass(cls, ext_point):
                extension_point = ext_point
                break

        if extension_point is None:
            msg = "Class {cls} doesn't match any extension point"
            msg = msg.format(cls=cls.__module__+'.'+cls.__name__)
            raise exceptions.ExtensionManagerError(msg)

        # Check for name colision
        if cls.__extension_name__ in self._registry[extension_point]:
            msg = ("Class {cls} can't be registered, name already registered "
                   "by {other}")
            msg = msg.format(
                cls=cls.__name__,
                other=self._registry[extension_point][cls.__extension_name__].__name__)
            raise exceptions.ExtensionManagerError(msg)

        self._registry[extension_point][cls.__extension_name__] = cls

        # Plain registry type
        #
        # if cls.__extension_name__ in self._registry:
        #     msg = ("Class {cls} can't be registered, name already registered "
        #            "by {other}")
        #     msg = msg.format(
        #         cls=cls.__name__,
        #         other=self._registry[cls.__extension_name__].__name__)
        #     raise ValueError(msg)

        # self._registry[cls.__extension_name__] = cls

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

    def get_extension_class(self, extension_point, name):
        if not issubclass(extension_point, Extension):
            msg = ("extension_point must be a subclass of "
                   "appkit.extensionmanager.Extension.")
            raise TypeError(msg)

        if not isinstance(name, str):
            msg = "name must be a str"
            raise TypeError(msg)

        return self._registry[extension_point][name]

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

    def get_extension(self, extension_point, name, *args, **kwargs):
        return self.get_extension_class(extension_point, name)(*args, **kwargs)

    def get_implementations(self, extension_point):
        if extension_point not in self._registry:
            msg = "{cls} is not a valid extension point"
            msg = msg.format(cls=extension_point.__name__)
            raise TypeError(msg)

        return list(self._registry[extension_point].values())
