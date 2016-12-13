import argparse
import sys


from appkit import extensionmanager
from appkit import logging
from appkit.extension import Extension


class BaseApp(extensionmanager.ExtensionManager):
    def __init__(self, name, logger=None):
        if logger is None:
            logger = logging.get_logger('extension-manager')

        super().__init__(name, logger=logger)
        self.logger = logging.get_logger(name)


class ServiceAppMixin:
    def __init__(self):
        self.register_extension_point(Service)
        self._services = {}

    def register_extension_class(self, cls):
        BaseApp.register_extension_class(self, cls)
        if issubclass(cls, Service):
            self._services[cls.__extension_name__] = cls(self)

    def get_extension(self, extension_point, name, *args, **kwargs):
        try:
            return self._services[name]
        except KeyError:
            BaseApp.get_instance(self, extension_point, name, *args, **kwargs)


class CommandlineAppMixin:
    def __init__(self):
        self.register_extension_point(Command)

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
        # Build full argument parser
        argparser = self.build_argument_parser()
        subparser = argparser.add_subparsers(
            title='subcommands',
            dest='subcommand',
            description='valid subcommands',
            help='additional help')

        commands = self.get_implementations(Command)

        if len(commands) == 1:
            # Single command mode
            commands[0].setup_argparser(argparser)

        else:
            # Multiple command mode
            subargparsers = {}
            for cmdcls in commands:
                cmdname = cmdcls.__extension_name__

                subargparsers[cmdname] = subparser.add_parser(
                    cmdname,
                    help=cmdcls.help)
                cmdcls.setup_argparser(subargparsers[cmdname])

        # Parse arguments
        args = argparser.parse_args(args)
        if not args.subcommand:
            argparser.print_help()
            return

        # Get extension instances and extract its argument names
        ext = self.get_extension(args.subcommand)
        try:
            return ext.run(args)
        except CommandArgumentError as e:
            subargparsers[args.subcommand].print_help()
            print("\nError message: {}".format(e), file=sys.stderr)

        # except (arroyo.exc.BackendError,
        #         arroyo.exc.NoImplementationError) as e:
        #     self.logger.critical(e)

        raise NotImplementedError()

    def run_from_args(self):
        self.run(*sys.argv[1:])


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

    def run(self, args):
        raise NotImplementedError()


class CommandArgumentError(Exception):
    pass


def cliargument(*args, **kwargs):
    """
    argparse argument wrapper to ease the command argument definitions
    """
    def wrapped_arguments():
        return args, kwargs

    return wrapped_arguments
