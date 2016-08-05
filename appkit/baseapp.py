from appkit import extension
from appkit import extensionmanager
from appkit import logging


class BaseApp(extensionmanager.ExtensionManager):
    def __init__(self, name):
        super().__init__(name, logger=logging.get_logger('extension-manager'))
        self.logger = logging.get_logger(name)

    def get_extension(self, name, *args, **kwargs):
        return self.get_extension_class(name)(self, *args, **kwargs)


class BaseExtension(extension.Extension):
    def __init__(self, app):
        super().__init__()
        self.app = app
