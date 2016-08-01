import itertools
from glob import fnmatch

_undef = object()
_str_booleans = (
    '0', '1',
    'no', 'yes',
    'n', 'y',
    'false', 'true'
)


class NonEmptyStr(str):
    pass


def cast_value(v, req_type):
    if isinstance(v, req_type):
        return v

    if req_type is int:
        return int(v)

    if req_type is NonEmptyStr:
        v = str(v)
        if v is None or v == '':
            raise ValueError(v)
        return v

    if req_type is bool:
        if isinstance(v, str) and v.lower() in _str_booleans:
            return v in (
                x for (idx, x) in enumerate(_str_booleans) if idx % 2
            )
        else:
            raise ValueError(v)

    try:
        return req_type(v)
    except ValueError as e:
        raise ValueError(v) from e


def type_validator(type_table, cast=False, relaxed=False):
    def _validator(k, v):
        # Check for exact match
        if k in type_table:
            try:
                return cast_value(v, type_table[k])
            except ValueError:
                pass
            raise TypeError(k + ": invalid type")

        # Check wildcards (regexps in the future?)
        for (candidate_key, candidate_type) in type_table.items():
            if fnmatch.fnmatch(k, candidate_key):
                try:
                    return cast_value(v, candidate_type)
                except ValueError():
                    pass
                raise TypeError(k + ": invalid type")

        # No matches
        if relaxed:
            return v

        # Finally raise a typeerror
        raise TypeError(k + ": can't validate")

    return _validator


class Store(dict):
    """
    Key-value store using a namespace schema.
    Namespace separator is dot ('.') character
    """
    def __init__(self, d={}, validator=None):
        super(Store, self).__init__()

        self._validators = {}
        self._namespaces = set()

        if validator:
            self.set_validator(validator)

        for (k, v) in d.items():
            self.__setitem__(k, v)

    def set(self, key, value):
        return self.__setitem__(key, value)

    def get(self, key, default=_undef):
        if key in self:
            return self.__getitem__(key)

        elif default is not _undef:
            return default

        else:
            raise KeyError(key)

    def delete(self, key):
        return self.__delitem__(key)

    @staticmethod
    def get_namespaces(key):
        parts = key.split('.')
        return ('.'.join(parts[0:i+1]) for i in range(len(parts)-1))

    def has_namespace(self, namespace):
        return namespace in self._namespaces

    def set_validator(self, func, ns=None, recheck=True):
        if ns in self._validators:
            raise Exception('Validator conflict')

        self._validators[ns] = func

        if recheck:
            # Dont use .children method here
            subkeys = self.keys()
            if ns:
                s = ns + '.'
                subkeys = filter(lambda k: k.startswith(s), subkeys)

            for k in subkeys:
                self.set(k, self.get(k))

    def find_validator(self, key):
        for ns in reversed([None] + list(self.get_namespaces(key))):
            if ns in self._validators:
                return self._validators[ns]

    def __setitem__(self, key, value):
        if not isinstance(key, str) or key == '':
            raise TypeError(key)

        validator = self.find_validator(key)
        if validator:
            value = validator(key, value)

        for x in self.get_namespaces(key):
            self._namespaces.add(x)

        super().__setitem__(key, value)

    def get_tree(self, namespace, default=_undef):
        if namespace not in self._namespaces:
            if default is _undef:
                raise KeyError(namespace)
            else:
                return default

        r = {}
        idx = len(namespace) + 1
        for subkey in self.children(namespace, fullpath=True):
            if subkey in self._namespaces:
                r[subkey[idx:]] = self.get_tree(subkey)
            else:
                r[subkey[idx:]] = self.get(subkey)

        return r

    def __delitem__(self, key):
        if key in self._namespaces:
            children = list(self.children(key, fullpath=True))
            for child in children:
                del(self[child])
            self._namespaces.remove(key)

        if key in self:
            super().__delitem__(key)

    def children(self, key, fullpath=False):
        s = key + '.'
        r = itertools.chain((k for k in self), self._namespaces)

        # Filter children…
        r = filter(lambda k: k.startswith(s), r)

        # …but not grandchildrens
        r = filter(lambda k: '.' not in k[len(s):], r)

        # Full or short path?
        if not fullpath:
            r = map(lambda k: k[len(s):], r)

        return r

    def load_configparser(self, cp, root_sections=()):
        def is_root(x):
            return x in root_sections

        kvs = {}

        for s in filter(is_root, cp.sections()):
            kvs.update({k: v for (k, v) in cp[s].items()})

        for s in filter(lambda x: not is_root(x), cp.sections()):
            kvs.update({s + '.' + k: v for (k, v) in cp[s].items()})

        for (k, v) in kvs.items():
            self.set(k, v)

    def load_arguments(self, args):
        for (k, v) in vars(args).items():
            self.set(k, v)
