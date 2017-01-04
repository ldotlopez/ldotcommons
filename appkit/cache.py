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


from appkit import types

import os
import pickle
import shutil
import tempfile
import time

from hashlib import sha1


def hashfunc(key):
    return sha1(key.encode('utf-8')).hexdigest()


class NullCache:
    def __init__(self, *args, **kwargs):
        pass

    def get(self, key):
        raise CacheMissError()

    def set(self, key, data):
        pass


class DiskCache:
    def __init__(self, basedir=None, delta=-1, hashfunc=hashfunc,
                 logger=None):
        self.basedir = basedir
        self.delta = delta
        self._is_tmp = False
        self._logger = logger or types.NullSingleton()

        if not self.basedir:
            self.basedir = tempfile.mkdtemp()
            self._is_tmp = True

    def _on_disk_path(self, key):
        hashed = hashfunc(key)
        return os.path.join(
            self.basedir, hashed[:0], hashed[:1], hashed[:2], hashed)

    def set(self, key, value):
        p = self._on_disk_path(key)
        dname = os.path.dirname(p)

        if not os.path.exists(dname):
            os.makedirs(dname)

        with open(p, 'wb') as fh:
            fh.write(pickle.dumps(value))

    def get(self, key, delta=None):
        on_disk = self._on_disk_path(key)
        try:
            s = os.stat(on_disk)

        except (OSError, IOError) as e:
            raise CacheMissError() from e

        delta = delta or self.delta
        if delta >= 0 and \
           (time.mktime(time.localtime()) - s.st_mtime > delta):
            msg = "Key «{key}» is outdated"
            msg = msg.format(key=key)
            self._logger.debug(msg)
            os.unlink(on_disk)

            raise CacheMissError()

        try:
            with open(on_disk, 'rb') as fh:
                msg = "Found «{key}»: '{path}'"
                msg = msg.format(key=key, path=on_disk)
                self._logger.debug(msg)

                return pickle.loads(fh.read())

        except (IOError, OSError) as e:
            msg = "Error accessing «{key}»: {reason}"
            msg = msg.format(key=key, reason=str(e))
            self._logger.error(msg)

            raise CacheMissError() from e

    def __del__(self):
        if self._is_tmp:
            shutil.rmtree(self.basedir)


class DeprecatedDiskCache(DiskCache):
    def get(self, key):
        try:
            super().get(key)
        except CacheMissError:
            return None


class CacheError(Exception):
    pass


class CacheMissError(CacheError):
    pass
