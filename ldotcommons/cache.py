# -*- encoding: utf-8 -*-

from ldotcommons import utils

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
        self._is_tmp = False
        self._basedir = basedir
        self._delta = delta
        self._logger = logger or utils.NullSingleton()

        if not self._basedir:
            self._basedir = tempfile.mkdtemp()
            self._is_tmp = True

    def _on_disk_path(self, key):
        hashed = hashfunc(key)
        return os.path.join(
            self._basedir, hashed[:0], hashed[:1], hashed[:2], hashed)

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
        except OSError:
            return None
        except IOError:
            return None

        if self._delta >= 0 and \
           (time.mktime(time.localtime()) - s.st_mtime > self._delta):
            self._logger.debug('Key {0} is outdated'.format(key))
            os.unlink(on_disk)
            return None

        try:
            self._logger.debug('Using cache: {}'.format(on_disk))
            with open(on_disk, 'rb') as fh:
                buff = pickle.loads(fh.read())
            return buff

        except FileNotFoundError:
            return None

        except (OSError, IOError) as e:
            msg = 'Failed access to key {key}: {reason}'
            msg = msg.format(key=key, reason=str(e))
            self._logger.error(msg)
            try:
                os.unlink(on_disk)
            except:
                pass

            return None

    def __del__(self):
        if self._is_tmp:
            shutil.rmtree(self._basedir)
