import abc
import argparse
import collections
import sys


from appkit import extensionmanager
from appkit import logging
from appkit.extension import Extension


class Service(Extension):
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

    @abc.abstractmethod
    def run(self, app, args):
        raise NotImplementedError()


class BaseApp(extensionmanager.ExtensionManager):
    def __init__(self, name, logger=None):
        if logger is None:
            logger = logging.get_logger('extension-manager')

        super().__init__(name, logger=logger)
        self.logger = logging.get_logger(name)


class ServiceAppMixin:
    SERVICE_EXTENSION_POINT = Service

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_extension_point(self.__class__.SERVICE_EXTENSION_POINT)
        self._services = {}

    def register_extension_class(self, cls):
        BaseApp.register_extension_class(self, cls)
        if issubclass(cls, self.__class__.SERVICE_EXTENSION_POINT):
            self._services[cls.__extension_name__] = cls(self)

    def get_extension(self, extension_point, name, *args, **kwargs):
        assert isinstance(extension_point, type)
        assert isinstance(name, str)

        # Check requested extension is a service
        if extension_point == self.__class__.SERVICE_EXTENSION_POINT and \
           name in self._services:
            return self._services[name]

        return super().get_extension(extension_point, name,
                                     *args, **kwargs)

    def get_service(self, name):
        return self.get_extension(self.__class__.SERVICE_EXTENSION_POINT, name)


class CommandlineAppMixin:
    COMMAND_EXTENSION_POINT = Command

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_extension_point(self.__class__.COMMAND_EXTENSION_POINT)

    @classmethod
    def build_argument_parser(cls):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument(
            '-h', '--help',
            action='store_true',
            dest='help')

        parser.add_argument(
            '-v', '--verbose',
            dest='verbose',
            default=0,
            action='count')

        parser.add_argument(
            '-q', '--quiet',
            dest='quiet',
            default=0,
            action='count')

        parser.add_argument(
            '-c', '--config-file',
            dest='config-files',
            action='append',
            default=[])

        parser.add_argument(
            '--plugin',
            dest='plugins',
            action='append',
            default=[])

        return parser

    def run(self, *args):
        assert (isinstance(args, collections.Iterable))
        assert all([isinstance(x, str) for x in args])

        argparser = self.build_argument_parser()

        commands = list(self.get_implementations(
            self.__class__.COMMAND_EXTENSION_POINT).values())

        if len(commands) == 1:
            # Single command mode
            commands[0].setup_argparser(argparser)
            args = argparser.parse_args(args)
            ext = commands[0]

        else:
            subparser = argparser.add_subparsers(
                title='subcommands',
                dest='subcommand',
                description='valid subcommands',
                help='additional help')

            # Multiple command mode
            subargparsers = {}
            for cmdcls in commands:
                cmdname = cmdcls.__extension_name__

                subargparsers[cmdname] = subparser.add_parser(
                    cmdname,
                    help=cmdcls.help)
                cmdcls.setup_argparser(subargparsers[cmdname])

            args = argparser.parse_args(args)
            if not args.subcommand:
                argparser.print_help()
                return

            # Get extension instances and extract its argument names
            ext = self.get_extension(self.__class__.COMMAND_EXTENSION_POINT,
                                     args.subcommand)

        try:
            return ext.run(self, args)
        except CommandArgumentError as e:
            subargparsers[args.subcommand].print_help()
            print("\nError message: {}".format(e), file=sys.stderr)

        raise NotImplementedError()

    def run_from_args(self):
        self.run(*sys.argv[1:])


class CommandArgumentError(Exception):
    pass


def cliargument(*args, **kwargs):
    """
    argparse argument wrapper to ease the command argument definitions
    """
    def wrapped_arguments():
        return args, kwargs

    return wrapped_arguments
