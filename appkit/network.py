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


class AsyncFetcher:
    def __init__(self, logger=None, cache=None, max_requests=1,
                 timeout=-1,
                 **session_options):
        self._logger = logger
        self._cache = cache
        self._semaphore = asyncio.Semaphore(max_requests)
        self._session = aiohttp.ClientSession(**session_options)

    @property
    def session(self):
        return self._session

    @asyncio.coroutine
    def fetch(self, url, **request_options):
        resp, content = yield from self.fetch_full(url,
                                                   **request_options)

        return content

    @asyncio.coroutine
    def fetch_full(self, url, skip_cache=False, timeout=0, **request_options):
        use_cache = not skip_cache and self._cache

        if use_cache:
            buff = self._cache.get(url)
            if buff:
                return None, buff

        with (yield from self._semaphore):
            with AsyncTimeout(timeout):
                if self._logger:
                    msg = "Fetching «{url}»"
                    msg = msg.format(url=url)
                    self._logger.info(msg)

                resp = yield from self.session.get(url, **request_options)
                buff = yield from resp.content.read()
                yield from resp.release()

        if use_cache:
            self._cache.set(url, buff)

        return resp, buff

    def __del__(self):
        self.session.close()


class AsyncTimeout(aiohttp.Timeout):
    def __init__(self, t):
        super().__init__(t)
        self.t = t

    def __enter__(self, *args, **kwargs):
        if self.t > 0:
            return super().__enter__(*args, **kwargs)

    def __exit__(self, *args, **kwargs):
        if self.t > 0:
            return super().__exit__(*args, **kwargs)
