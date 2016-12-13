# -*- encoding: utf-8 -*-

from appkit import utils

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
        return None

    def set(self, key, data):
        pass


class DiskCache:
    def __init__(self, basedir=None, delta=-1, hashfunc=hashfunc,
                 logger=None):
        self.basedir = basedir
        self.delta = delta
        self._is_tmp = False
        self._logger = logger or utils.NullSingleton()

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

    def get(self, key):
        on_disk = self._on_disk_path(key)
        try:
            s = os.stat(on_disk)
        except (OSError, IOError):
            return None

        if self.delta >= 0 and \
           (time.mktime(time.localtime()) - s.st_mtime > self.delta):
            msg = "Key «{key}» is outdated"
            msg = msg.format(key=key)
            self._logger.debug(msg)
            os.unlink(on_disk)
            return None

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

            try:
                os.unlink(on_disk)
            except:
                pass

    def __del__(self):
        if self._is_tmp:
            shutil.rmtree(self.basedir)
