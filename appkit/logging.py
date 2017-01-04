# -*- coding: utf-8 -*-

# Copyright (C) 2015 Luis López
# Copyright (C) 2012 Jacobo Tarragón
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

import functools
import logging

try:
    import colorama
    _has_color = True
except ImportError:
    _has_color = False

from appkit import utils


LOGGING_FORMAT = "[%(levelname)s] [%(name)s] %(message)s"

_loggers = dict()
_log_level = logging.DEBUG

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL


class EncodedStreamHandler(logging.StreamHandler):
    if _has_color:
        _color_map = {
            'DEBUG': colorama.Fore.CYAN,
            'INFO': colorama.Fore.GREEN,
            'WARNING': colorama.Fore.YELLOW,
            'ERROR': colorama.Fore.RED,
            'CRITICAL': colorama.Back.RED,
        }
    else:
        _color_map = {}

    def __init__(self, encoding='utf-8', *args, **kwargs):
        super(EncodedStreamHandler, self).__init__(*args, **kwargs)
        self.encoding = encoding
        self._color_reset = b''
        self.terminator = self.terminator.encode(self.encoding)
        if _has_color:
            colorama.init()
            self._color_map = {k: v.encode(self.encoding)
                               for (k, v) in self._color_map.items()}
            self._color_reset = colorama.Style.RESET_ALL.encode(self.encoding)

    def emit(self, record):
        try:
            msg = self.format(record).encode(self.encoding)
            stream = self.stream
            if _has_color:
                msg = (
                    self._color_map.get(record.levelname, b'') +
                    msg +
                    self._color_reset
                )

            stream.buffer.write(msg)
            stream.buffer.write(self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def set_level(level):
    global _loggers
    global _log_level

    _log_level = level
    for (name, logger) in _loggers.items():
        logger.setLevel(level)


def get_logger(key=None):
    global _loggers
    global _log_level

    if key is None:
        key = utils.prog_name()

    if key not in _loggers:
        _loggers[key] = logging.getLogger(key)
        _loggers[key].setLevel(_log_level)

        handler = EncodedStreamHandler()
        handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
        _loggers[key].addHandler(handler)

    return _loggers[key]


def log_on_success(msg='done', level=20):
    """
    logs `msg` with `level` at the end of the method call
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapped_fn(self, *args, **kwargs):
            logger = getattr(self, 'logger')
            ret = fn(self, *args, **kwargs)
            if logger:
                logger.log(level, msg)
            return ret
        return wrapped_fn
    return decorator
