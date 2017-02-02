import collections
import functools
import re

UNDEFINED = object()


def _namespace_validate_key(f):
    @functools.wraps(f)
    def wrapper(ns, key, *args, **kwargs):
        is_string = isinstance(key, str)
        matches_re = '.' in key or re.match(r'^[a-z0-9]+$', key, re.IGNORECASE)
        starts_with_dot = key[0] == '.'
        ends_with_dot = key[-1] == '.'

        if not is_string or not matches_re or starts_with_dot or ends_with_dot:
            msg = ("key must be a alphanumerical, non empty string. "
                   "Got: {} (isstr:{}, re:{}, starts:{}, ends:{}")
            msg = msg.format(
                repr(key), is_string, matches_re, starts_with_dot, ends_with_dot)
            raise TypeError(msg)

        return f(ns, key, *args, **kwargs)

    return wrapper


def flatten_dict(d):
    if not isinstance(d, dict):
        raise TypeError()

    ret = {}

    for (k, v) in d.items():
        if isinstance(v, dict):
            subret = flatten_dict(v)
            subret = {k + '.' + subk: subv
                      for (subk, subv) in
                      subret.items()}
            ret.update(subret)
        else:
            ret[k] = v

    return ret


class KeyUsedAsNamespaceError(KeyError):
    pass


class Namespace(collections.abc.Mapping):
    """
    Possible exceptions:
        KeyUsedAsNamespaceError(KeyError)
        KeyError
        TypeError
    Implements:
        Collection: __contains__
        Mapping: __setitem__, __delitem__,
        MutableMapping: __getitem__, __iter__, __len__
    """

    def __init__(self, *args, **kwargs):
        super().__init__()

        self._d = dict()
        for arg in args:
            if not isinstance(arg, collections.Mapping):
                raise ValueError(arg)

            for (k, v) in arg.items():
                self[k] = v

        for (k, v) in kwargs.items():
            self[k] = v

    def delete(self, item):
        del(self[item])

    def set(self, item, value):
        """
        Wrapper around __setitem__

        No direct access to _d
        """
        self[item] = value

    def get(self, item, default=UNDEFINED):
        """
        Wrapper around __getitem__
        Adds default value for item functionality

        No direct access to _d
        """
        try:
            return self[item]
        except KeyError:
            if default is not UNDEFINED:
                return default
            else:
                raise

    def __len__(self):
        return len([x for x in self])

    @_namespace_validate_key
    def __delitem__(self, item):
        if '.' not in item:
            del(self._d[item])
            return

        key, subkey = item.split('.', 1)
        ns = self[key]
        if not isinstance(ns, Namespace):
            raise KeyUsedAsNamespaceError(key, 'Not a namespace')

        del(ns[subkey])

    @_namespace_validate_key
    def __contains__(self, item):
        """
        Support for 'in' operator

        Access to _d: Check if item in _d
        """
        if '.' not in item:
            return item in self._d

        key, subkey = item.split('.', 1)
        try:
            ns = self[key]
        except KeyError:
            return False

        return subkey in ns

    @_namespace_validate_key
    def __setitem__(self, item, value):
        """
        Support for Mapping[item]

        Access to _d: Store value in _d
        """
        if '.' not in item:
            self._d[item] = value
            return

        key, subkey = item.split('.', 1)
        ns = self.get(key, Namespace())
        if not isinstance(ns, Namespace):
            raise KeyUsedAsNamespaceError(key, 'Not a namespace')

        ns[subkey] = value
        self[key] = ns

    @_namespace_validate_key
    def __getitem__(self, item):
        """
        Support for Mapping[item]

        Access to _d: Access value in _d
        """
        if '.' not in item:
            return self._d[item]

        key, subkey = item.split('.', 1)
        ns = self[key]

        if not isinstance(ns, Namespace):
            raise KeyUsedAsNamespaceError(key)

        try:
            return ns[subkey]

        except KeyUsedAsNamespaceError:
            raise

        except KeyError as e:
            raise KeyError(item) from e

    def __iter__(self):
        """
        Support for Mapping __iter__

        Access to _d: get items
        """
        for (item, value) in self._d.items():
            if isinstance(value, Namespace):
                yield from (item + "." + subitem for subitem in value)
            else:
                yield item

    def __repr__(self):
        """
        Suport for obj.__repr__

        No direct access to _d
        """
        return "<Namespace({data}) at {i}>".format(
            data=", ".join(['{}={}'.format(k, v) for (k, v) in self.items()]),
            i=hex(id(self))
        )

    def children(self, item=None):
        if item is None:
            ns = self
        else:
            ns = self[item]

        return list(ns._d.keys())

    def asdict(self):
        return {k: self[k].asdict()
                if isinstance(self[k], Namespace) else self[k]
                for k in self.children()}
