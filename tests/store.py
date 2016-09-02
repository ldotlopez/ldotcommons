# -*- coding: utf-8 -*-
# [SublimeLinter pep8-max-line-length:160 flake8-max-line-length:160]
# vim: set fileencoding=utf-8 :

import unittest

from ldotcommons import store


class TestStore(unittest.TestCase):
    def test_get_set(self):
        s = store.Store()

        s.set('x', 1)
        self.assertEqual(s.get('x'), 1)
        self.assertEqual(s.get(None), {'x': 1})

    def test_delete(self):
        s = store.Store()

        s.set('x', 1)
        s.delete('x')
        with self.assertRaises(store.KeyNotFoundError) as cm:
            s.get('x')
        self.assertEqual(cm.exception.args[0], 'x')

        self.assertEqual(s.get(None), {})

    def test_get_with_default(self):
        s = store.Store()

        self.assertEqual(s.get('foo', default=3), 3)
        self.assertEqual(s.get('foo', default='x'), 'x')
        with self.assertRaises(store.KeyNotFoundError) as cm:
            s.get('foo')
        self.assertEqual(cm.exception.args[0], 'foo')

        self.assertEqual(s.get(None), {})

    def test_all_keys(self):
        s = store.Store()
        s.set('x', 1)
        s.set('y.a', 2)
        s.set('y.b', 2)

        self.assertEqual(
            set(s.all_keys()),
            set(['x', 'y.a', 'y.b']))

    def test_has_key(self):
        s = store.Store()
        s.set('x', 1)
        s.set('y.a', 2)
        s.set('y.b', 2)

        self.assertTrue(s.has_key('x'))
        self.assertTrue(s.has_key('y'))
        self.assertTrue(s.has_key('y.a'))

    def test_has_ns(self):
        s = store.Store()
        s.set('x', 1)
        s.set('y.a', 2)
        s.set('y.b', 2)

        self.assertFalse(s.has_namespace('x'))
        self.assertFalse(s.has_namespace('y.a'))
        self.assertTrue(s.has_namespace('y'))
        self.assertFalse(s.has_namespace('z'))

    def test_override(self):
        s = store.Store()
        s.set('x', 1)
        s.set('x', 'a')
        self.assertEqual(s.get('x'), 'a')
        self.assertEqual(s.get(None), {'x': 'a'})

    def test_empty(self):
        s = store.Store()
        s.set('x', 1)
        s.empty()

        self.assertFalse(s.has_key('x'))

    def test_replace(self):
        s = store.Store()
        s.set('x', 1)
        s.replace({'y': 2})

        self.assertFalse(s.has_key('x'))
        self.assertTrue(s.has_key('y'))

    def test_override_with_dict(self):
        s = store.Store()
        s.set('x', 1)
        s.set('x', 'a')
        self.assertEqual(s.get('x'), 'a')
        self.assertEqual(s.get(None), {'x': 'a'})

    def test_key_not_found(self):
        s = store.Store()

        with self.assertRaises(store.KeyNotFoundError) as cm:
            s.get('y')
        self.assertEqual(cm.exception.args[0], 'y')

        self.assertEqual(s.get(None), {})

    def test_children(self):
        s = store.Store()
        s.set('a.b.x', 1)
        s.set('a.b.y', 2)
        s.set('a.b.z', 3)
        s.set('a.c.w', 4)

        self.assertEqual(
            set(s.children('a.b')),
            set(['x', 'y', 'z']))

        self.assertEqual(
            set(s.children('a')),
            set(['b', 'c']))

        self.assertEqual(
            s.children(None),
            ['a'])

    def test_complex(self):
        s = store.Store()

        s.set('a.b.c', 3)
        self.assertEqual(s.get('a.b.c'), 3)
        self.assertEqual(s.get('a.b'), {'c': 3})
        self.assertEqual(s.get('a'), {'b': {'c': 3}})
        self.assertEqual(s.get(None), {'a': {'b': {'c': 3}}})

        s.set('a.k.a', 1)
        s.delete('a.b')
        self.assertEqual(s.get(None), {'a': {'k': {'a': 1}}})

        with self.assertRaises(store.KeyNotFoundError) as cm:
            s.get('a.b')
        self.assertEqual(cm.exception.args[0], 'a.b')

    def test_validator_simple(self):
        def validator(k, v):
            if k == 'int' and not isinstance(v, int):
                raise store.ValidationError(k, v, 'not int')

            return v

        s = store.Store()
        s.add_validator(validator)

        s.set('int', 1)
        with self.assertRaises(store.ValidationError):
            s.set('int', 'a')

    def test_validator_alters_value(self):
        def validator(k, v):
            if k == 'int' and not isinstance(v, int):
                try:
                    v = int(v)
                except ValueError:
                    raise store.ValidationError(k, v, 'not int')

            return v

        s = store.Store()
        s.add_validator(validator)

        s.set('int', 1.1)
        self.assertEqual(s.get('int'), 1)
        with self.assertRaises(store.ValidationError):
            s.set('int', 'a')

    def test_illegal_keys(self):
        s = store.Store()

        with self.assertRaises(store.IllegalKeyError):
            s.set(1, 1)

        with self.assertRaises(store.IllegalKeyError):
            s.set('.x', 1)

        with self.assertRaises(store.IllegalKeyError):
            s.set('.x', 1)

        with self.assertRaises(store.IllegalKeyError):
            s.set('x.', 1)

        with self.assertRaises(store.IllegalKeyError):
            s.set('x..a', 1)

    def test_conflict_validator(self):
        def val(key, value):
            return value

        s = store.Store()

        s.add_validator(val, None)
        with self.assertRaises(store.ValidatorConflictError):
            s.add_validator(val, None)

    def test_multivalidators(self):
        called = 0

        def root_validator(k, v):
            nonlocal called
            called += 1
            return v

        def int_validator(k, v):
            return v - 1

        def str_validator(k, v):
            return ''.join(reversed(list(iter(v))))

        s = store.Store()
        s.add_validator(root_validator)
        s.add_validator(int_validator, 'int')
        s.add_validator(str_validator, 'str')

        s.set('int', 10)
        s.set('str', 'xyz')

        self.assertEqual(called, 2)
        self.assertEqual(s.get('int'), 9)
        self.assertEqual(s.get('str'), 'zyx')

    def test_dottet_value(self):
        s = store.Store()
        s.set('a.b', 'c.d')
        self.assertEqual(s.get('a.b'), 'c.d')

if __name__ == '__main__':
    unittest.main()
