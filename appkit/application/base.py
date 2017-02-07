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


import warnings


from appkit import extensionmanager
from appkit import logging


class Extension(extensionmanager.Extension):
    pass


class BaseApplication(extensionmanager.ExtensionManager):
    def __init__(self, name, pluginpath=None, logger=None):
        if pluginpath is not None:
            warnings.warn('pluginpath is ignored')

        if logger is None:
            logger = logging.getLogger('extension-manager')

        super().__init__(name)
        self.logger = logging.getLogger(name)


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


class RequirementError(ExtensionError):
    pass


def cliargument(*args, **kwargs):
    """
    argparse argument wrapper to ease the command argument definitions
    """
    def wrapped_arguments():
        return args, kwargs

    return wrapped_arguments
