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


import copy
import json


from appkit import deprecations
from appkit.namespace import (
    Namespace,
    KeyUsedAsNamespaceError,
    flatten_dict,
    UNDEFINED
)


class FormatError(Exception):
    pass


class IllegalKeyError(deprecations.DeprecatedClass, TypeError):
    def __unicode__(self):
        return "Illegal key: '{}'".format(self.args[0])

    __str__ = __unicode__


class KeyNotFoundError(deprecations.DeprecatedClass, KeyError):
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


class StoreNative:
    def __init__(self, items={}, validators=[]):
        self._d = {}
        self._validators = []

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
        for vfunc in self._validators:
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
        buff = json.dumps(self.get(None), sort_keys=True, indent=4)
        stream.write(buff)

    def load(self, stream):
        try:
            data = flatten_dict(json.loads(stream.read()))
        except json.decoder.JSONDecodeError as e:
            raise FormatError() from e

        for (k, v) in data.items():
            self.set(k, v)

    def load_arguments(self, args):
        for (k, v) in vars(args).items():
            self.set(k, v)

    def add_validator(self, fn):
        self._validators.append(fn)

    def set(self, key, value):
        subkey, d = self._get_subdict(key, create=True)
        v = self._process_value(key, value)
        d[subkey] = v

    def get(self, key, default=UNDEFINED):
        if key is None:
            return self._d

        try:
            subkey, d = self._get_subdict(key, create=False)
            return copy.deepcopy(d[subkey])

        except (KeyNotFoundError, KeyError) as e:
            if default != UNDEFINED:
                return copy.deepcopy(default)
            else:
                raise KeyNotFoundError(key) from e

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
        try:
            subkey, d = self._get_subdict(key)
        except KeyNotFoundError:
            return False

        return subkey in d

    def has_namespace(self, ns):
        try:
            subns, d = self._get_subdict(ns)
        except KeyNotFoundError:
            return False

        return subns in d and isinstance(d[subns], dict)

    __contains__ = has_key
    __setitem__ = get
    __setitem__ = set
    __delitem__ = delete


class StoreAdaptor(Namespace):
    def __init__(self, items={}, validators=[]):
        super().__init__(**items)
        self._validators = []

        for validator in validators:
            self.add_validator(validator)

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError as e:
            raise KeyNotFoundError(e.args[0]) from e

    def __setitem__(self, key, value):
        try:
            for vfunc in self._validators:
                value = vfunc(key, value)
            return super().__setitem__(key, value)
        except TypeError as e:
            raise IllegalKeyError(e.args[0]) from e

    def get(self, item, default=UNDEFINED):
        if item is None:
            return self.asdict()

        return super().get(item, default)

    def add_validator(self, fn):
        self._validators.append(fn)

    def dump(self, stream):
        buff = json.dumps(self.get(None), sort_keys=True, indent=4)
        stream.write(buff)

    def load(self, stream):
        try:
            data = flatten_dict(json.loads(stream.read()))
        except json.decoder.JSONDecodeError as e:
            raise FormatError() from e

        for (k, v) in data.items():
            self.set(k, v)

    def load_arguments(self, args):
        for (k, v) in vars(args).items():
            self.set(k, v)

    @deprecations.deprecatedmethod
    def all_keys(self):
        return list(iter(self))

    @deprecations.deprecatedmethod
    def empty(self):
        keys = list(self.keys())
        for key in keys:
            del(self[key])

    @deprecations.deprecatedmethod
    def has_key(self, item):
        return item in self

    @deprecations.deprecatedmethod
    def has_namespace(self, ns):
        ns = self.get(ns, None)
        return isinstance(ns, Namespace)

    @deprecations.deprecatedmethod
    def replace(self, *args, **kwargs):
        self.empty()
        Namespace.__init__(self, *args, **kwargs)


Store = StoreAdaptor
