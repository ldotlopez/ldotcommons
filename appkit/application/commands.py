import abc
import argparse
import collections
import sys

from appkit import application


class Command(application.Extension):
    HELP = ''
    ARGUMENTS = ()

    def setup_argparser(self, cmdargparser):
        for argument in self.ARGUMENTS:
            args, kwargs = argument()
            cmdargparser.add_argument(*args, **kwargs)

    @abc.abstractmethod
    def execute(self, app, args):
        raise NotImplementedError()


class CommandManager:
    COMMAND_EXTENSION_POINT = Command

    def __init__(self, app):
        app.register_extension_point(self.__class__.COMMAND_EXTENSION_POINT)
        self.app = app

    @classmethod
    def build_base_argument_parser(cls):
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

    def get_commands(self):
        yield from self.app.get_extensions_for(
            self.__class__.COMMAND_EXTENSION_POINT)

    def call_execute_method(self, command, arguments):
        return command.execute(self, arguments)

    def execute(self, *args):
        assert (isinstance(args, collections.Iterable))
        assert all([isinstance(x, str) for x in args])

        argparser = self.build_base_argument_parser()
        commands = list(self.get_commands())

        if len(commands) == 1:
            # Single command mode
            (cmdname, cmdext) = commands[0]
            cmdext.setup_argparser(argparser)
            args = argparser.parse_args(args)

        else:
            subparser = argparser.add_subparsers(
                title='subcommands',
                dest='subcommand',
                description='valid subcommands',
                help='additional help')

            # Multiple command mode
            subargparsers = {}
            for (cmdname, cmdext) in commands:
                subargparsers[cmdname] = subparser.add_parser(
                    cmdname,
                    help=cmdext.HELP)
                cmdext.setup_argparser(subargparsers[cmdname])

            args = argparser.parse_args(args)
            if not args.subcommand:
                argparser.print_help()
                return

            cmdname = args.subcommand

        try:
            # Reuse commands
            tmp = dict(commands)
            self.call_execute_method(tmp[cmdname], args)

        except application.ArgumentsError as e:
            if len(commands) > 1:
                subargparsers[args.subcommand].print_help()
            else:
                argparser.print_help()

            print("\nError message: {}".format(e), file=sys.stderr)

        except Exception as e:
            msg = "Unhandled exception «{exctype}» from «{name}»: {e}"
            msg = msg.format(
                exctype=e.__class__.__module__ + '.' + e.__class__.__name__,
                name=tmp[cmdname].__class__,
                e=str(e))
            self.app.logger.critical(msg)
            raise

    def execute_from_command_line(self):
        self.execute(*sys.argv[1:])
