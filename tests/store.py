# -*- coding: utf-8 -*-
# [SublimeLinter pep8-max-line-length:160 flake8-max-line-length:160]
# vim: set fileencoding=utf-8 :

import unittest

from appkit.namespace import (
    Namespace,
    KeyUsedAsNamespaceError,
    flatten_dict
)

from appkit.store import (
    # Legacy
    Store,
    IllegalKeyError,
    KeyNotFoundError,
    ValidationError
)


class NamespaceTest(unittest.TestCase):
    def test_get_set(self):
        ns = Namespace(x=1)
        self.assertEqual(ns.get('x'), 1)

    def test_deep_set_get_deep(self):
        ns = Namespace()

        ns.set('a.b.c', 1)
        self.assertEqual(
            ns.get('a.b.c'),
            1)

        a_ns = ns.get('a')
        self.assertTrue(isinstance(a_ns, Namespace))
        self.assertEqual(
            a_ns.get('b.c'),
            1)

        b_ns = a_ns.get('b')
        self.assertTrue(isinstance(b_ns, Namespace))
        self.assertEqual(
            b_ns.get('c'),
            1)

        ns = Namespace()
        ns.set('x.y', 1)
        ns.set('x.z', 1)

    def test_complex_set(self):
        items = {
            'a': 1,
            'b': 2,
            'x': {
                'y': {
                    'z': 3
                }
            }
        }
        ns = Namespace()
        for (k, v) in flatten_dict(items).items():
            ns.set(k, v)

        self.assertEqual(
            ns,
            Namespace(
                a=1,
                b=2,
                x=Namespace(
                    y=Namespace(
                        z=3
                    )
                )
            )
        )

    def test_delete(self):
        ns = Namespace(x=1)
        del(ns['x'])

        self.assertFalse('x' in ns)

    def test_deep_delete(self):
        ns = Namespace()
        ns.set('a', 1)
        ns.set('x.y.z', 1)
        del(ns['x.y.z'])

        self.assertFalse('x.y.z' in ns)
        self.assertTrue('x.y' in ns)

        ns = Namespace()
        ns.set('x.y', 0)
        ns.set('a', 0)
        del(ns['x'])

        self.assertFalse('x.y' in ns)
        self.assertFalse('x' in ns)
        self.assertTrue('a' in ns)

    def test_namespace_get_restriction(self):
        ns = Namespace(key='value')

        with self.assertRaises(KeyUsedAsNamespaceError) as cm:
            ns.get('key.foo')
        self.assertEqual(cm.exception.args[0], 'key')

        with self.assertRaises(KeyUsedAsNamespaceError) as cm:
            ns.get('key.foo.bar')
        self.assertEqual(cm.exception.args[0], 'key')

    def test_namespace_set_restriction(self):
        ns = Namespace(key='value')

        with self.assertRaises(KeyUsedAsNamespaceError) as cm:
            ns.set('key.foo', 1)
        self.assertEqual(cm.exception.args[0], 'key')

        with self.assertRaises(KeyUsedAsNamespaceError) as cm:
            ns.set('key.foo.bar', 1)
        self.assertEqual(cm.exception.args[0], 'key')

    def test_get_with_default(self):
        ns = Namespace()

        x = object()
        self.assertEqual(
            ns.get('foo', default=x),
            x)

        self.assertEqual(
            ns.get('x.y.z', default=x),
            x)

    def test_get_with_default_value_doesnt_alter_ns(self):
        ns = Namespace()

        ns.get('a', default=1)
        with self.assertRaises(KeyError):
            ns.get('a')

    def test_missing_key(self):
        ns = Namespace()
        with self.assertRaises(KeyError) as cm:
            ns.get('a')
        self.assertEqual(cm.exception.args[0], 'a')

    def test_complex_missing_key(self):
        ns = Namespace()
        with self.assertRaises(KeyError) as cm:
            ns.get('a.b.c')
        self.assertEqual(cm.exception.args[0], 'a')

    def test_partial_missing_key(self):
        ns = Namespace()
        ns.set('a', Namespace())

        # Partial missing key
        with self.assertRaises(KeyError) as cm:
            ns.get('a.b')
        self.assertEqual(cm.exception.args[0], 'a.b')

    def test_contains(self):
        ns = Namespace(a=1)

        self.assertTrue('a' in ns)
        self.assertFalse('b' in ns)

    def test_deep_contains(self):
        ns = Namespace(x=1, a=Namespace(b=2))

        self.assertTrue('x' in ns)
        self.assertTrue('a.b' in ns)
        self.assertFalse('a.c' in ns)

    def test_iter(self):
        keys = [
            'a',
            'x.y.z',
        ]
        ns = Namespace({k: None for k in keys})
        self.assertEqual(
            set(keys),
            set(list(ns.keys()))
        )

    def test_children(self):
        keys = [
            'a',
            'b',
            'x.y.z'
        ]
        ns = Namespace({k: None for k in keys})
        self.assertEqual(
            set(['a', 'b', 'x']),
            set(ns.children())
        )

    def test_asdict(self):
        ns = Namespace(a=1)
        self.assertEqual(
            ns.asdict(),
            {'a': 1})

        ns = Namespace(
            a=1,
            x=Namespace(
                y=Namespace(
                    z=None)))

        self.assertEqual(
            ns.asdict(),
            {'a': 1, 'x': {'y': {'z': None}}})


class StoreTest(unittest.TestCase):
    def test_get_set(self):
        s = Store()

        s.set('x', 1)
        self.assertEqual(s.get('x'), 1)
        self.assertEqual(s.get(None), {'x': 1})

    def test_delete(self):
        s = Store()

        s.set('x', 1)
        s.delete('x')
        with self.assertRaises(KeyNotFoundError) as cm:
            s.get('x')
        self.assertEqual(cm.exception.args[0], 'x')

        self.assertEqual(s.get(None), {})

    def test_get_with_default(self):
        s = Store()

        self.assertEqual(s.get('foo', default=3), 3)
        self.assertEqual(s.get('foo', default='x'), 'x')
        with self.assertRaises(KeyNotFoundError) as cm:
            s.get('foo')
        self.assertEqual(cm.exception.args[0], 'foo')

        self.assertEqual(s.get(None), {})

    def test_all_keys(self):
        s = Store()
        s.set('x', 1)
        s.set('y.a', 2)
        s.set('y.b', 2)

        self.assertEqual(
            set(s.all_keys()),
            set(['x', 'y.a', 'y.b']))

    def test_has_key(self):
        s = Store()
        s.set('x', 1)
        s.set('y.a', 2)
        s.set('y.b', 2)

        self.assertTrue(s.has_key('x'))
        self.assertTrue(s.has_key('y'))
        self.assertTrue(s.has_key('y.a'))

    def test_has_ns(self):
        s = Store()
        s.set('x', 1)
        s.set('y.a', 2)
        s.set('y.b', 2)

        self.assertFalse(s.has_namespace('x'))
        self.assertFalse(s.has_namespace('y.a'))
        self.assertTrue(s.has_namespace('y'))
        self.assertFalse(s.has_namespace('z'))

    def test_override(self):
        s = Store()
        s.set('x', 1)
        s.set('x', 'a')
        self.assertEqual(s.get('x'), 'a')
        self.assertEqual(s.get(None), {'x': 'a'})

    def test_empty(self):
        s = Store()
        s.set('x', 1)
        s.empty()

        self.assertFalse(s.has_key('x'))

    def test_replace(self):
        s = Store()
        s.set('x', 1)
        s.replace({'y': 2})

        self.assertFalse(s.has_key('x'))
        self.assertTrue(s.has_key('y'))

    def test_override_with_dict(self):
        s = Store()
        s.set('x', 1)
        s.set('x', 'a')
        self.assertEqual(s.get('x'), 'a')
        self.assertEqual(s.get(None), {'x': 'a'})

    def test_key_not_found(self):
        s = Store()

        with self.assertRaises(KeyNotFoundError) as cm:
            s.get('y')
        self.assertEqual(cm.exception.args[0], 'y')

        self.assertEqual(s.get(None), {})

    def test_children(self):
        s = Store()
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
        return
        s = Store()

        s.set('a.b.c', 3)
        self.assertEqual(s.get('a.b.c'), 3)
        self.assertEqual(s.get('a.b'), {'c': 3})
        self.assertEqual(s.get('a'), {'b': {'c': 3}})
        self.assertEqual(s.get(None), {'a': {'b': {'c': 3}}})

        s.set('a.k.a', 1)
        s.delete('a.b')
        self.assertEqual(s.get(None), {'a': {'k': {'a': 1}}})

        with self.assertRaises(KeyNotFoundError) as cm:
            s.get('a.b')
        self.assertEqual(cm.exception.args[0], 'a.b')

    def test_validator_simple(self):
        def validator(k, v):
            if k == 'int' and not isinstance(v, int):
                raise ValidationError(k, v, 'not int')

            return v

        s = Store()
        s.add_validator(validator)

        s.set('int', 1)
        with self.assertRaises(ValidationError):
            s.set('int', 'a')

    def test_validator_alters_value(self):
        def validator(k, v):
            if k == 'int' and not isinstance(v, int):
                try:
                    v = int(v)
                except ValueError:
                    raise ValidationError(k, v, 'not int')

            return v

        s = Store()
        s.add_validator(validator)

        s.set('int', 1.1)
        self.assertEqual(s.get('int'), 1)
        with self.assertRaises(ValidationError):
            s.set('int', 'a')

    def test_illegal_keys(self):
        s = Store()

        with self.assertRaises(IllegalKeyError):
            s.set(1, 1)

        with self.assertRaises(IllegalKeyError):
            s.set('.x', 1)

        with self.assertRaises(IllegalKeyError):
            s.set('.x', 1)

        with self.assertRaises(IllegalKeyError):
            s.set('x.', 1)

        with self.assertRaises(IllegalKeyError):
            s.set('x..a', 1)

    def test_dottet_value(self):
        s = Store()
        s.set('a.b', 'c.d')
        self.assertEqual(s.get('a.b'), 'c.d')

if __name__ == '__main__':
    unittest.main()
