# -*- encoding: utf-8 -*-


import importlib
import re
import warnings


from appkit import types


class Extension:
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
        # because we can't have parents and childrens registered at the same
        # time.
        # DON'T uncomment the next line keep it as a reminder
        #
        # self.register_extension_point(Extension)

    # Notes on terminology:
    # someplugin.py -> plugin (package)
    # SomeExtensionClass -> extension_point
    # SubClassImplementingSomeExtensionClass -> extension_class
    # instance of SubClassImplementingSomeExtensionType -> extension

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

    def register_extension_point(self, extension_point):
        def check_subclass(a, b):
            return issubclass(a, b) or issubclass(b, a)

        full_cls_name = "{}.{}".format(
            extension_point.__module__, extension_point.__name__)

        # Check "class-iness"
        if extension_point.__class__ != type:
            msg = "Extension point must be a class"
            raise TypeError(msg)

        # Check base type
        if not issubclass(extension_point, Extension):
            msg = ("Class {cls} is not a valid extension "
                   "(must a subclass of appkit.app.Extension)")
            msg = msg.format(cls=full_cls_name)
            raise TypeError(msg)

        # Distinguish between extension points and extension classes
        if hasattr(extension_point, '__extension_name__'):
            msg = "Attempt to register an extension as extension point"
            raise TypeError(msg)

        # Avoid duplicated extension points
        if extension_point in self._registry:
            msg = "Extension point {clsname} already registered"
            msg = msg.format(clsname=extension_point.__name__)
            raise ExtensionManagerError(msg)

        # Avoid inter-subclassing between extension points
        for ext_point in self._registry:
            if check_subclass(extension_point, ext_point):
                msg = ("Extension point {cls1} is a subclass of {cls2} "
                       "(or viceversa)")
                msg = msg.format(cls1=extension_point.__name__,
                                 cls2=ext_point.__name__)
                raise ExtensionManagerError(msg)

        self._registry[extension_point] = {}

    def register_extension_class(self, extension_cls):
        full_cls_name = "{}.{}".format(
            extension_cls.__module__, extension_cls.__name__)

        # Check "class-iness"
        if extension_cls.__class__ != type:
            msg = "Extension point must be a class"
            raise TypeError(msg)

        # Check base type
        if not issubclass(extension_cls, Extension):
            msg = ("Class {cls} is not a valid extension "
                   "(must a subclass of appkit.app.Extension)")
            msg = msg.format(cls=full_cls_name)
            raise TypeError(msg)

        # Check for mandatory __extension_name__' attr
        if not hasattr(extension_cls, '__extension_name__'):
            msg = ("Class {cls} is not a valid extension "
                   "(must define a __extension_name__' attribute)")
            msg = msg.format(cls=full_cls_name)
            raise TypeError(msg)

        # Search for matching extension point
        extension_point = None
        for ext_point in self._registry:
            if issubclass(extension_cls, ext_point):
                extension_point = ext_point
                break

        if extension_point is None:
            msg = "Class {cls} doesn't match any extension point"
            msg = msg.format(cls=full_cls_name)
            raise ExtensionManagerError(msg)

        # Check for name colision
        extension_name = extension_cls.__extension_name__
        if extension_name in self._registry[extension_point]:
            msg = ("Class {cls} can't be registered, name already registered "
                   "by {other}")
            other = self._registry[extension_point][extension_name]
            msg = msg.format(
                cls=extension_cls.__name__,
                other=other.__name__)
            raise ExtensionManagerError(msg)

        self._registry[extension_point][extension_name] = extension_cls

    def _get_extension_class(self, extension_point, name):
        if not issubclass(extension_point, Extension):
            msg = ("extension_point must be a subclass of "
                   "appkit.extensionmanager.Extension.")
            raise TypeError(msg)

        if not isinstance(name, str):
            msg = "name must be a str"
            raise TypeError(msg)

        if extension_point not in self._registry:
            msg = "Invalid extension_point '{cls}'"
            msg = msg.format(cls=extension_point.__module__ +
                             '.' + extension_point.__name__)
            raise TypeError(msg)

        return self._registry[extension_point][name]

    def get_extensions_for(self, extension_point, *args, **kwargs):
        assert extension_point in self._registry

        yield from ((name, self.get_extension(
                        extension_point, name, *args, **kwargs))
                    for name in self._registry[extension_point])

    def get_extension(self, extension_point, name, *args, **kwargs):
        cls = self._get_extension_class(extension_point, name)
        return cls(*args, **kwargs)


class ExtensionManagerError(Exception):
    pass


class PluginNotLoadedError(Exception):
    pass


class PluginWithoutExtensionsError(Exception):
    pass
