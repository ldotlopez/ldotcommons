from appkit import extension
from appkit import extensionmanager


class App(extensionmanager.ExtensionManager):
    def get_extension(self, name, *args, **kwargs):
        return self.get_extension_class(name)(self, *args, **kwargs)

    def run(self, *args):
        raise NotImplementedError()


class Extension(extension.Extension):
    def __init__(self, app):
        super().__init__()
        self.app = app


class Command(Extension):
    help = ''
    arguments = ()

    @classmethod
    def setup_argparser(cls, cmdargparser):
        arguments = getattr(cls, 'arguments')
        for argument in arguments:
            args, kwargs = argument()
            cmdargparser.add_argument(*args, **kwargs)

    def run(self, arguments):
        raise NotImplementedError()


def argument(*args, **kwargs):
    """
    argparse argument wrapper to ease the command argument definitions
    """
    def wrapped_arguments():
        return args, kwargs

    return wrapped_arguments
