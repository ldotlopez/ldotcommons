# -*- coding: utf-8 -*-

# Copyright (C) 2015 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


import abc
import argparse
import collections
import sys
import warnings


from appkit import extensionmanager
from appkit import logging


class Extension(extensionmanager.Extension):
    pass


class Command(extensionmanager.Extension):
    help = ''
    arguments = ()

    def setup_argparser(self, cmdargparser):
        arguments = getattr(self, 'arguments')
        for argument in arguments:
            args, kwargs = argument()
            cmdargparser.add_argument(*args, **kwargs)

    @abc.abstractmethod
    def execute(self, app, args):
        raise NotImplementedError()


class Service(extensionmanager.Extension):
    def __init__(self, app):
        super().__init__()
        self.app = app


class BaseApplication(extensionmanager.ExtensionManager):
    def __init__(self, name, pluginpath=None, logger=None):
        if pluginpath is not None:
            warnings.warn('pluginpath is ignored')

        if logger is None:
            logger = logging.getLogger('extension-manager')

        super().__init__(name, logger=logger)
        self.logger = logging.getLogger(name)


class ServiceApplicationMixin:
    SERVICE_EXTENSION_POINT = Service

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register_extension_point(self.__class__.SERVICE_EXTENSION_POINT)
        self._services = {}

    def register_extension_class(self, cls):
        BaseApplication.register_extension_class(self, cls)
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


class CommandlineApplicationMixin:
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

    def get_commands(self):
        yield from self.get_extensions_for(
            self.__class__.COMMAND_EXTENSION_POINT)

    def execute_command_extension(self, command, arguments):
        return command.execute(self, arguments)

    def execute(self, *args):
        assert (isinstance(args, collections.Iterable))
        assert all([isinstance(x, str) for x in args])

        argparser = self.build_argument_parser()
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
                    help=cmdext.help)
                cmdext.setup_argparser(subargparsers[cmdname])

            args = argparser.parse_args(args)
            if not args.subcommand:
                argparser.print_help()
                return

            cmdname = args.subcommand

        try:
            # Reuse commands
            tmp = dict(commands)
            self.execute_command_extension(tmp[cmdname], args)

        except ArgumentsError as e:
            if len(commands) > 1:
                subargparsers[args.subcommand].print_help()
            else:
                argparser.print_help()

            print("\nError message: {}".format(e), file=sys.stderr)

    def execute_from_command_line(self):
        self.execute(*sys.argv[1:])


class ExtensionNotFoundError(extensionmanager.ExtensionNotFoundError):
    pass


class ExtensionError(Exception):
    """
    Generic extension error
    """
    pass


class ConfigurationError(ExtensionError):
    pass


class ArgumentsError(ExtensionError):
    pass


def cliargument(*args, **kwargs):
    """
    argparse argument wrapper to ease the command argument definitions
    """
    def wrapped_arguments():
        return args, kwargs

    return wrapped_arguments
