import asyncio
import functools
import gzip
import io
import socket
import sys

from os import path
from urllib import request, error as urllib_error

import aiohttp

from . import cache, exceptions, logging, utils


class FetchError(exceptions.Exception):
    pass


class Fetcher:
    def __new__(cls, fetcher_name, *args, **kwargs):
        clsname = fetcher_name.replace('-', ' ').replace('_', ' ').capitalize()
        clsname = clsname + 'Fetcher'

        mod = sys.modules[__name__]
        cls = getattr(mod, clsname)
        return cls(*args, **kwargs)


class BaseFetcher(object):
    def fetch(self, url, **opts):
        raise NotImplementedError('Method not implemented')


class MockFetcher(BaseFetcher):
    def __init__(self, basedir=None, **opts):
        self._basedir = basedir

    def fetch(self, url, **opts):
        if not self._basedir:
            raise FetchError("MockFetcher basedir is not configured")

        url = utils.slugify(url)

        e = None
        f = path.join(self._basedir, url)
        try:
            fh = open(f)
            buff = fh.read()
            fh.close()

            return buff

        except IOError as e:
            msg = "{msg} '{path}' (errno {code})"
            msg = msg.format(msg=e.args[1], code=e.args[0], path=f)
            raise FetchError(msg) from e


class UrllibFetcher(BaseFetcher):
    def __init__(self, headers={}, enable_cache=False, cache_delta=-1,
                 logger=None):
        if not logger:
            logger = logging.get_logger('ldotcommons.fetchers.urllibfetcher')

        self._logger = logger

        if enable_cache:
            cache_path = utils.user_path(
                'cache', 'urllibfetcher', create=True, is_folder=True)

            self._cache = cache.DiskCache(
                basedir=cache_path, delta=cache_delta,
                logger=self._logger.getChild('cache'))

            msg = 'UrllibFetcher using cache {path}'
            msg = msg.format(path=cache_path)
            self._logger.debug(msg)
        else:
            self._cache = cache.NullCache()

        self._headers = headers

    def fetch(self, url, **opts):
        buff = self._cache.get(url)
        if buff:
            self._logger.debug("found in cache: {}".format(url))
            return buff

        try:
            req = request.Request(url, headers=self._headers, **opts)
            resp = request.urlopen(req)
            if resp.getheader('Content-Encoding') == 'gzip':
                bi = io.BytesIO(resp.read())
                gf = gzip.GzipFile(fileobj=bi, mode="rb")
                buff = gf.read()
            else:
                buff = resp.read()
        except (socket.error, urllib_error.HTTPError) as e:
            raise FetchError("{message}".format(message=e))

        self._logger.debug("stored in cache: {}".format(url))
        self._cache.set(url, buff)
        return buff


class AIOHttpFetcher:
    def __init__(self, enable_cache=False, cache_delta=60*5,
                 logger=None):
        if enable_cache:
            cache_path = utils.user_path(
                'cache', 'fetcher', create=True, is_folder=True)

            self._cache = cache.DiskCache(
                basedir=cache_path, delta=cache_delta, logger=logger)

        else:
            self._cache = cache.NullCache()

        self._loop = asyncio.get_event_loop()

    @asyncio.coroutine
    def fetch(self, url, **opts):
        buff = yield from self._loop.run_in_executor(
            None,
            functools.partial(self._cache.get, url)
        )
        if buff:
            return buff

        with aiohttp.ClientSession(**opts) as client:
            resp = yield from client.get(url)
            buff = yield from resp.content.read()
            yield from resp.release()

        yield from self._loop.run_in_executor(
            None,
            functools.partial(self._cache.set, url, buff)
        )

        return buff
