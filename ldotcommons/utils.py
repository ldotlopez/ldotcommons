import argparse
import configparser
import datetime
import importlib
import os
import re
import sys
import time
import urllib.parse
import warnings

import appdirs


NoneType = type(None)


class DictAction(argparse.Action):

    """
    Convert a series of --foo key=value --foo key2=value2 into a dict like:
    { key: value, key2: value}
    """

    def __call__(self, parser, namespace, values, option_string=None):
        dest = getattr(namespace, self.dest)
        if dest is None:
            dest = {}

        parts = values.split('=')
        key = parts[0]
        value = ''.join(parts[1:])

        dest[key] = value

        setattr(namespace, self.dest, dest)


class InmutableDict(dict):
    _msg = "'InmutableDict' object does not support operation"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ = True

    def pop(self, key):
        if getattr(self, '_', False):
            raise TypeError(self._msg)

        super().pop(key)

    def exclude(self, *keys):
        return InmutableDict({k: v for (k, v) in self.items()
                              if k not in keys})

    def clear(self):
        if getattr(self, '_', False):
            raise TypeError(self._msg)

        super().clear()

    def __setitem__(self, key, value):
        if getattr(self, '_', False):
            raise TypeError(self._msg)

        super().__setitem__(key, value)

    def __delitem__(self, key):
        if getattr(self, '_', False):
            raise TypeError(self._msg)

        super().__delitem__(key)


class MultiDepthDict(dict):

    def subdict(self,
                prefix, strip_prefix=True, separator='.', merge_parent=False):
        full_prefix = prefix + separator

        return {k[len(full_prefix):] if strip_prefix else k: v
                for (k, v) in self.items() if k.startswith(full_prefix)}


class SingletonMetaclass(type):
    def __call__(cls, *args, **kwargs):  # nopep8
        instance = getattr(cls, '_instance', None)
        if not instance:
            setattr(cls,
                    '_instance',
                    super(SingletonMetaclass, cls).__call__(*args, **kwargs))
        return cls._instance


class ReadOnlyAttribute(Exception):
    pass


# class AttribDict(dict):
#     RO = []
#     GETTERS = []
#     SETTERS = []

#     def _setter(self, attr, value):
#         try:
#             return self.__setitem__(attr, value)
#         except KeyError:
#             raise AttributeError(attr)

#     def _getter(self, attr):
#         try:
#             return self.__getitem__(attr)
#         except KeyError:
#             raise AttributeError(attr)

#     def __getattr__(self, attr):
#         if attr in self.__class__.GETTERS:
#             return getattr(self, 'get_' + attr)()

#         try:
#             return super(AttribDict, self).__getitem__(attr)
#         except KeyError:
#             raise AttributeError(attr)

#     def __setattr__(self, attr, value):
#         if attr in self.__class__.RO:
#             raise ReadOnlyAttribute()

#         if attr in self.__class__.SETTERS:
#             import ipdb; ipdb.set_trace()
#             return getattr(self, 'set_' + attr)(value)()

#         try:
#             return super(AttribDict, self).__setitem__(attr, value)
#         except KeyError:
#             raise AttributeError(attr)

#     def __setitem__(self, key, value):
#         try:
#             return self.__setattr__(key, value)
#         except AttributeError:
#             pass

#         raise KeyError(key)

#     def __getitem__(self, key):
#         try:
#             return self.__getattr__(key)
#         except AttributeError:
#             pass

#         raise KeyError(key)

class AttribDict(dict):
    RO = []
    GETTERS = []
    SETTERS = []

    def _setter(self, attr, value):
        try:
            return self.__setitem__(attr, value)
        except KeyError:
            raise AttributeError(attr)

    def _getter(self, attr):
        try:
            return self.__getitem__(attr)
        except KeyError:
            raise AttributeError(attr)

    def __getattr__(self, attr):
        if attr in self.__class__.GETTERS:
            return getattr(self, 'get_' + attr)()

        try:
            return super(AttribDict, self).__getitem__(attr)
        except KeyError:
            raise AttributeError(attr)

    def __setattr__(self, attr, value):
        if attr in self.__class__.RO:
            raise ReadOnlyAttribute()

        if attr in self.__class__.SETTERS:
            return getattr(self, 'set_' + attr)(value)

        try:
            return super(AttribDict, self).__setitem__(attr, value)
        except KeyError:
            raise AttributeError(attr)


class FactoryError(Exception):
    pass


class Factory:

    def _to_clsname(self, name):
        return ''.join([
            x.capitalize() for x in self._to_modname(name).split('_')
        ])

    def _to_modname(self, name):
        return name.replace('-', '_')

    def __init__(self, ns):
        self._ns = ns
        self._mod = importlib.import_module(ns)
        self._objs = {}

    def __call__(self, name, *args, **kwargs):
        if name not in self._objs:
            cls = None

            # Try loading class from internal mod
            try:
                cls = self._load_from_ns(name)
            except AttributeError:
                pass

            # Try loading from submodule
            if not cls:
                try:
                    cls = self._load_from_submod(name)
                except (ImportError, AttributeError):
                    pass

            # Module not found
            if not cls:
                raise FactoryError(
                    'Unable to load {} from namespace {}'.format(
                        name, self._ns)
                    )

            # Create and save obj into cache
            self._objs[name] = cls(*args, **kwargs)

        return self._objs[name]

    def _load_from_ns(self, name):
        return getattr(self._mod, self._to_clsname(name))

    def _load_from_submod(self, name):
        m = importlib.import_module(
            "{}.{}".format(self._ns, self._to_modname(name)))
        return getattr(m, self._to_clsname(name))


class ModuleFactory:
    def __init__(self, ns):
        self._ns = ns
        self._ns_sym = importlib.import_module(ns)
        self._m = {}

    def __call__(self, name):
        if name not in self._m:
            if hasattr(self._ns_sym, name):
                self._m[name] = getattr(self._ns_sym, name)

            else:
                try:
                    self._m[name] = importlib.import_module(
                        "{}.{}".format(self._ns, name))
                except ImportError:
                    pass

        return self._m[name]


class ObjectFactory:
    def __init__(self, ns, in_sub_module=True):
        self._ns = ns
        self._ns_sym = importlib.import_module(ns)
        self._m = {}
        self._in_sub_module = in_sub_module

    def __call__(self, name, *args, **kwargs):
        if name not in self._m:
            cls_name = ''.join([x.capitalize() for x in name.split('_')])

            if not self._in_sub_module:
                self._m[name] = getattr(self._ns_sym, cls_name)

            else:
                tmp = re.sub(r'([A-Z])', r'_\1', cls_name[1:])
                tmp = cls_name[0] + tmp

                sub_mod = None
                sub_mod_exceptions = {}

                for mod_candidate in [cls_name.lower(), tmp.lower()]:
                    try:
                        sub_mod = importlib.import_module("{}.{}".format(
                            self._ns, mod_candidate))
                        break

                    except ImportError as e:
                        sub_mod_exceptions[mod_candidate] = e
                        pass

                if not sub_mod:
                    raise IndexError(sub_mod_exceptions)

            self._m[name] = getattr(sub_mod, cls_name)

        return self._m[name](*args, **kwargs)


def url_strip_query_param(url, key):
    p = urllib.parse.urlparse(url)
    # urllib.parse.urllib.parse.parse_qs may return items in different order
    # that original, so we avoid use it
    qs = '&'.join(
        [x for x in p.query.split('&') if not x.startswith(key + '=')])

    return urllib.parse.ParseResult(
        p.scheme,
        p.netloc,
        p.path,
        p.params,
        qs,
        p.fragment).geturl()


def url_get_query_param(url, key, default=None):
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if key in q:
        return q[key][-1]
    else:
        return default


def prog_name(prog=sys.argv[0]):
    prog = os.path.basename(prog)
    prog = os.path.splitext(prog)[0]

    if appdirs.system == 'linux':
        prog = re.sub(r'[\-\s]+', '-', prog).lower()
    else:
        prog = ' '.join([x.capitalize() for x in re.split(r'[\-\s]+', prog)])

    return prog


def prog_config_file(prog=None):
    if prog is None:
        prog = prog_name()

    return user_path('config') + '.ini'


def slugify(s, max_len=0, allowed_chars=r'a-zA-Z0-9\-\.'):
    s = re.sub(r'[^' + allowed_chars + r']', '-', s)
    return s[:max_len] if max_len > 0 else s


def user_path(typ, name=None, prog=None, create=False, is_folder=None):
    m = {
        'config': appdirs.user_config_dir,
        'data': appdirs.user_data_dir,
        'cache': appdirs.user_cache_dir
    }

    if prog is None:
        prog = prog_name()

    if is_folder is None:
        is_folder = name is None

    if typ not in m:
        raise ValueError("Invalid user_path type: '{type}'".format(type=typ))

    ret = m[typ](prog)
    if name is not None:
        # Fix name for OSX
        if appdirs.system == 'darwin':
            name = os.path.sep.join([x.capitalize()
                                    for x in name.split(os.path.sep)])
        ret = os.path.join(m[typ](prog), name)

    if create:
        if is_folder is True:
            mkdir_target = ret
        else:
            mkdir_target = os.path.split(ret)[0]

        if not os.path.exists(mkdir_target):
            os.makedirs(mkdir_target)

    return ret


def shortify(s, length=50):
    """
    Returns a shortified version of s
    """
    return "…" + s[-(length - 1):] if len(s) > length else s


def utcnow_timestamp():
    warnings.warn('Use ldotcommons.utils.now_timestamp(utc=True)')
    return now_timestamp(utc=True)


def now_timestamp(utc=False):
    dt = datetime.datetime.utcnow() if utc else datetime.datetime.now()
    return int(time.mktime(dt.timetuple()))


def configparser_to_dict(cp):
    return {section:
            {k: v for (k, v) in cp[section].items()}
            for section in cp.sections()}


def ini_load(path):
    cp = configparser.ConfigParser()
    with open(path, 'r') as fh:
        cp.read_file(fh)

    return configparser_to_dict(cp)


def ini_dump(d, path):
    cp = configparser.ConfigParser()

    for (section, pairs) in d.items():
        cp[section] = {k: v for (k, v) in pairs.items()}

    fh = open(path, 'w+')
    cp.write(fh)
    fh.close()


def parse_interval(string):
    _table = {
        'S': 1,
        'M': 60,
        'H': 60*60,
        'd': 60*60*24,
        'w': 60*60*24*7,
        'm': 60*60*24*30,
        'y': 60*60*24*365,
    }
    if isinstance(string, (int)):
        string = str(string)

    if not isinstance(string, str):
        raise TypeError(string)

    m = re.match(r'^(?P<amount>\d+)\s*(?P<modifier>[SMHdwmy])?$', string)
    if not m:
        raise ValueError(string)

    amount = int(m.group('amount'))
    multiplier = _table.get(m.group('modifier') or 'S')
    return amount*multiplier


def parse_size(string):
    suffixes = ['k', 'm', 'g', 't', 'p', 'e', 'z', 'y']
    _table = {key: 1000 ** (idx + 1)
              for (idx, key) in enumerate(suffixes)}

    string = string.replace(',', '.')
    m = re.search(r'^([0-9\.]+)\s*([kmgtphezy]b?)?$', string.lower())
    if not m:
        raise ValueError()

    value = m.group(1)
    mod = m.group(2)

    if '.' in value:
        value = float(value)
    else:
        value = int(value)

    if mod in _table:
        value = value * _table[mod]

    return value


def parse_date(string):
    _table = [
        (r'^\d{4}.\d{2}.\d{2}.\d{2}.\d{2}', '%Y %m %d %H %M'),
        (r'^\d{4}.\d{2}.\d{2}$', '%Y %m %d'),
        (r'^\d{4}.\d{2}$', '%Y %m')
    ]

    if isinstance(string, int):
        return string

    string = re.sub(r'[:\.\-\s/]', ' ', string)

    for (regexp, fmt) in _table:
        if not re.search(regexp, string):
            continue

        dt = datetime.datetime.strptime(string, fmt)
        return int(time.mktime(dt.timetuple()))

    raise ValueError(string)


def _import(obj):
    mod = __import__(obj)
    for o in obj.split('.')[1:]:
        mod = getattr(mod, o)
    return mod


def word_split(s):
    ret = []
    idx = 0
    protected = False

    for c in s:
        # Setup element
        if len(ret) <= idx:
            ret.insert(idx, '')

        if c in ('\'', '"'):
            protected = not protected
            continue

        if c == ' ' and not protected:
            idx += 1
        else:
            ret[idx] += c


def ichunks(it, size):
    """
    Generator function.
    Yields slices with "size"  elements from it iterable.
    Last slice could have less elements.
    """
    while True:
        ret = []
        for x in range(size):
            try:
                ret.append(next(it))
            except StopIteration:
                if ret:
                    yield ret
                return

        yield ret
