import asyncio
import functools
import gzip
import io
import socket
import sys

from os import path
from urllib import request, error as urllib_error

import aiohttp

from . import cache, exceptions, utils


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
    def __init__(self,
                 user_agent=None, headers={},
                 enable_cache=False, cache_delta=-1,
                 logger=None, **opts):

        # Configure logger
        self._logger = logger or utils.NullSingleton()

        # Display errors
        for o in opts:
            msg = "Ignoring unsupported option: '{option}'"
            msg = msg.format(option=o)
            self._logger.warning(msg)

        # Setup headers
        self._headers = headers
        if user_agent:
            self._headers['User-Agent'] = user_agent

        # Setup cache
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

    def fetch(self, url, **opts):
        buff = self._cache.get(url)
        if buff:
            self._logger.debug("found in cache: {}".format(url))
            return buff

        headers = self._headers.copy()
        if 'headers' in opts:
            headers.update(opts['headers'])

        if 'user_agent' in opts:
            headers['User-Agent'] = opts['user_agent']

        try:
            req = request.Request(url, headers=headers, **opts)
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
    def __init__(self,
                 user_agent=None, headers={},
                 enable_cache=False, cache_delta=-1,
                 logger=None, **opts):
        # Configure logger
        self._logger = logger or utils.NullSingleton()

        # Display errors
        for o in opts:
            msg = "Ignoring unsupported option: '{option}'"
            msg = msg.format(option=o)
            self._logger.warning(msg)

        # Setup headers
        self._headers = headers
        if user_agent:
            self._headers['User-Agent'] = user_agent

        # Setup cache
        if enable_cache:
            cache_path = utils.user_path(
                'cache', 'aiohttpfetcher', create=True, is_folder=True)

            self._cache = cache.DiskCache(
                basedir=cache_path, delta=cache_delta,
                logger=self._logger.getChild('cache'))

            msg = 'AIOHttpFetcher using cache {path}'
            msg = msg.format(path=cache_path)
            self._logger.debug(msg)
        else:
            self._cache = cache.NullCache()

        self._loop = asyncio.get_event_loop()

    @asyncio.coroutine
    def fetch(self, url, **options):
        buff = yield from self._loop.run_in_executor(
            None,
            functools.partial(self._cache.get, url)
        )
        if buff:
            return buff

        opts = {'headers': self._headers}
        opts.update(opts)

        with aiohttp.ClientSession(**opts) as client:
            resp = yield from client.get(url)
            buff = yield from resp.content.read()
            yield from resp.release()

        yield from self._loop.run_in_executor(
            None,
            functools.partial(self._cache.set, url, buff)
        )

        return buff


class AIOHttpFetcherWithAcessControl:
    class Timeout(aiohttp.Timeout):
        def __init__(self, t):
            super().__init__(t)
            self.t = t

        def __enter__(self, *args, **kwargs):
            if self.t:
                return super().__enter__(*args, **kwargs)

        def __exit__(self, *args, **kwargs):
            if self.t:
                return super().__exit__(*args, **kwargs)

    def __init__(self,
                 logger=None,
                 enable_cache=False, cache_delta=-1,
                 max_reqs=1,
                 timeout=0,
                 **options):

        self.logger = logger

        # Setup cache
        if enable_cache:
            cache_path = utils.user_path(
                'cache', 'aiohttpfetcher', create=True, is_folder=True
            )

            self.cache = cache.DiskCache(
                basedir=cache_path, delta=cache_delta,
                logger=self.logger
            )

            msg = "{clsname} using cachepath '{path}'"
            msg = msg.format(clsname=self.__class__.__name__, path=cache_path)
            self.logger.debug(msg)
        else:
            self.cache = None

        self.cache_delta = cache_delta
        self.timeout = timeout
        self.options = options.copy()
        self.semaphore = asyncio.Semaphore(max_reqs)

        self.client = aiohttp.ClientSession(**self.options)

    @asyncio.coroutine
    def fetch(self, url, **options):
        if self.cache:
            buff = self.cache.get(url)
            if buff:
                return buff

        timeout = options.pop('timeout', None) or self.timeout
        opts = options or self.options

        with (yield from self.semaphore):
            with AIOHttpFetcherWithAcessControl.Timeout(timeout):
                if self.logger:
                    msg = "Fetching «{url}»"
                    msg = msg.format(url=url)
                    self.logger.info(msg)

                resp = yield from self.client.get(url, **opts)
                buff = yield from resp.content.read()
                yield from resp.release()

        if self.cache:
            self.cache.set(url, buff)

        return buff

    def __del__(self):
        self.client.close()
