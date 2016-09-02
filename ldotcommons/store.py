import copy


import yaml


_UNDEF = object()


class IllegalKeyError(ValueError):
    def __unicode__(self):
        return "Illegal key: '{}'".format(self.args[0])

    __str__ = __unicode__


class KeyNotFoundError(KeyError):
    def __unicode__(self):
        return "Key not found: '{}'".format(self.args[0])

    __str__ = __unicode__


class ValidationError(Exception):
    def __init__(self, key, value, msg):
        self.key = key
        self.value = value
        self.msg = msg

    def __unicode__(self):
        return "Invalid value {} for key '{}': {}".format(
            repr(self.value), self.key, self.msg or 'no reason')

    __str__ = __unicode__


class ValidatorConflictError(Exception):
    def __init__(self, msg, ns):
        super().__init__(msg)
        self.ns = ns


def flatten_dict(d):
    if not isinstance(d, dict):
        raise TypeError()

    ret = {}

    for (k, v) in d.items():
        if isinstance(v, dict):
            subret = flatten_dict(v)
            subret = {k + '.' + subk: subv for (subk, subv) in subret.items()}
            ret.update(subret)
        else:
            ret[k] = v

    return ret


class TypeValidator:
    def __init__(self, type_map):
        self.type_map = type_map

    def __call__(self, k, v):
        if k in self.type_map:
            try:
                return self.type_map[k](v)
            except:
                pass

            raise ValidationError(k, v, 'Incompatible type')

        return v


class Store:
    def __init__(self, items={}, validators=[]):
        self._d = {}
        self._validators = {}

        for validator in validators:
            self.add_validator(validator)

        self.update(items)

    def _process_key(self, key):
        if not isinstance(key, str):
            raise IllegalKeyError(key)

        parts = key.split('.')
        if not all(parts):
            raise IllegalKeyError(key)

        return parts

    def _process_value(self, key, value):
        for (ns, vfunc) in self._validators.items():
            if (
                    ns is None or
                    key == ns or
                    key.startswith(ns+".")):
                value = vfunc(key, value)

        return value

    def _get_subdict(self, key, create=False):
        d = self._d

        parts = self._process_key(key)
        for idx, p in enumerate(parts[:-1]):
            if p not in d and create:
                d[p] = {}

            # Override existing values with dicts is allowed
            # Subclass Store or use a validator if this behaviour needs to be
            # changed
            if p in d and not isinstance(d[p], dict):
                d[p] = {}

            if p not in d:
                raise KeyNotFoundError('.'.join(parts[:idx]))

            d = d[p]

        return parts[-1], d

    def empty(self):
        self._d = {}

    def replace(self, data):
        self.empty()
        self.update(data)

    def update(self, data):
        for (k, v) in flatten_dict(data).items():
            self.set(k, v)

    def dump(self, stream):
        stream.write(yaml.dump(self._d))

    def load(self, stream):

        d = flatten_dict(yaml.load(stream))
        for (k, v) in d.items():
            self.set(k, v)

    def load_arguments(self, args):
        for (k, v) in vars(args).items():
            self.set(k, v)

    def add_validator(self, fn, ns=None):
        if not callable(fn):
            msg = "fn argument must be a callable"
            raise TypeError(msg)

        if not (ns is None or (isinstance(ns, str) and ns != '')):
            msg = "ns argument must be None or a non empty string"
            raise TypeError(msg)

        if ns in self._validators:
            msg = "Another validator for «{ns}» is registered"
            msg = msg.format(ns=ns if ns is not None else '*')
            raise ValidatorConflictError(msg, ns=ns)

        self._validators[ns] = fn

        self.revalidate(ns)

    def revalidate(self, ns=None):
        if not (ns is None or (isinstance(ns, str) and str != '')):
            msg = "ns argument must be a non empty string"
            raise TypeError(msg)

        if not (self.has_namespace(ns) or self.has_key(ns)):
            return

        nsroot = ns + "." if ns is not None else ''
        nsdata = flatten_dict(self.get(ns))
        for (k, v) in nsdata.items():
            self.set(nsroot + k, v)

    def set(self, key, value):
        subkey, d = self._get_subdict(key, create=True)
        v = self._process_value(key, value)
        d[subkey] = v

    def get(self, key, default=_UNDEF):
        if key is None:
            return self._d

        try:
            subkey, d = self._get_subdict(key, create=False)
            return copy.deepcopy(d[subkey])

        except (KeyNotFoundError, KeyError):
            if default != _UNDEF:
                return copy.deepcopy(default)
            else:
                raise KeyNotFoundError(key)

    def delete(self, key):
        subkey, d = self._get_subdict(key)
        try:
            del(d[subkey])
            return
        except KeyError:
            pass  # Mask real exception

        raise KeyNotFoundError(key)

    def children(self, key=None):
        if key is None:
            return list(self._d.keys())

        subkey, d = self._get_subdict(key)
        try:
            return list(d[subkey].keys())
        except KeyError:
            raise KeyNotFoundError(key)

    def all_keys(self):
        return flatten_dict(self._d)

    def has_key(self, key):
        if key is None:
            return False

        try:
            subkey, d = self._get_subdict(key)
        except KeyNotFoundError:
            return False

        return subkey in d

    def has_namespace(self, ns):
        if ns is None:
            return True

        try:
            subns, d = self._get_subdict(ns)
        except KeyNotFoundError:
            return False

        return subns in d and isinstance(d[subns], dict)

    __contains__ = has_key
    __setitem__ = get
    __setitem__ = set
    __delitem__ = delete
