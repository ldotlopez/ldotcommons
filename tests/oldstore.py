import argparse
import configparser
import textwrap
import unittest
from ldotcommons import store


class TestStore(unittest.TestCase):
    def test_init(self):
        rd = store.Store({
            'x': 1,
            'y': 2,
            'foo.bar': 3.14
        })
        self.assertEqual(rd['x'], 1)
        self.assertEqual(rd['foo.bar'], 3.14)
        with self.assertRaises(KeyError):
            rd['a.b.c']

        rd = store.Store()
        rd['x'] = 1
        self.assertEqual(rd['x'], 1)
        with self.assertRaises(KeyError):
            rd['a.b.c']

    def test_setget(self):
        rd = store.Store()
        rd['x'] = 1

        self.assertEqual(rd['x'], 1)
        with self.assertRaises(KeyError):
            rd['y']

        with self.assertRaises(TypeError):
            rd[1.3] = 1

    def test_update(self):
        rd = store.Store({
            'x': 1,
            'y': 2,
            'foo.bar': 3,
            'foo.raz': 4
        })
        rd['x'] = 'x'
        rd['foo.raz'] = 'y'

        self.assertEqual(rd, {
            'x': 'x',
            'y': 2,
            'foo.bar': 3,
            'foo.raz': 'y'
        })

    def test_delete(self):
        rd = store.Store({
            'x': 1,
            'y': 2,
            'foo.bar': 3,
            'foo.raz': 4,
            'z.y.a': 5,
            'z.y.b': 6,
            'z.y.c': 7,
        })
        del rd['z.y.c']
        del rd['foo']

        self.assertEqual(rd, {
            'x': 1,
            'y': 2,
            'z.y.a': 5,
            'z.y.b': 6,
        })

    def test_contains(self):
        rd = store.Store({
            'x': 1,
            'y': 2,
            'foo.bar': 3,
            'foo.raz': 4,
            'z.y.a': 5,
            'z.y.b': 6,
            'z.y.c': 7,
        })
        self.assertTrue('x' in rd)
        self.assertTrue('z.y.a' in rd)
        self.assertFalse('bar' in rd)

    def test_keyerror(self):
        rd = store.Store({
            'x.y.z': None
        })
        with self.assertRaises(KeyError) as e:
            rd['x.y.foo']
        self.assertEqual(e.exception.args[0], 'x.y.foo')

    def test_tree(self):
        rd = store.Store({
            'a': 1,
            'b.aa': 2,
            'b.bb': 3,
            'c.aa.aaa': 4,
            'c.aa.bbb': 5,
            'c.aa.ccc': 6,
        })

        self.assertEqual(rd.get_tree('b'), {
            'aa': 2,
            'bb': 3,
        })
        self.assertEqual(rd.get_tree('c'), {
            'aa': {
                'aaa': 4,
                'bbb': 5,
                'ccc': 6
            }
        })
        self.assertEqual(rd.get_tree('c.aa'), {
            'aaa': 4,
            'bbb': 5,
            'ccc': 6
        })

    def test_builtin_validator(self):
        type_table = {
            'a': int,
            'b': float,
            'c': str,
            'x.y': int
        }

        d = {
            'a': 1,
            'b': 1.2,
            'c': 'foo',
            'x.y': 1
        }

        rd = store.Store(
            d=d,
            validator=store.type_validator(type_table, cast=False))

        rd['a'] = 2
        self.assertEqual(rd['a'], 2)

        with self.assertRaises(TypeError):
            rd['a'] = 'i want a int'

        with self.assertRaises(TypeError):
            rd['z'] = 'this key should not exist'

        with self.assertRaises(TypeError):
            rd['x'] = 'this is a namespace, not a key'

    def test_cast_validator(self):
        data = {
            'intkey': 1,
            'strkey': 'foo',
            'boolkey': True,
            'namespace.test': {'foo': 'bar'}
        }
        types = {
            'intkey': int,
            'strkey': str,
            'boolkey': bool,
            'namespace.test': dict,
            'namespace.test.foo': str
        }
        rd = store.Store(
            data,
            validator=store.type_validator(types, cast=True))

        rd['intkey'] = '8'
        rd['strkey'] = 0
        rd['boolkey'] = '0'
        rd['namespace.test.foo'] = 1
        self.assertEqual(rd['intkey'], 8)
        self.assertEqual(rd['strkey'], '0')
        self.assertEqual(rd['boolkey'], False)
        self.assertEqual(rd['namespace.test.foo'], '1')

    def test_relaxed_validator(self):
        data = {
            'defined': 1
        }
        types = {
            'defined': int
        }

        rd = store.Store(
            data,
            validator=store.type_validator(types, relaxed=True))
        with self.assertRaises(TypeError):
            rd['defined'] = 'foo'
        rd['undefined'] = object()

        rd = store.Store(
            data,
            validator=store.type_validator(types, relaxed=False))
        with self.assertRaises(TypeError):
            rd['undefined'] = object()
        rd['defined'] = 1

    def test_recheck(self):
        def validator(key, value):
            if key == 'int':
                try:
                    return int(value)
                except ValueError as e:
                    raise TypeError() from e

            return value

        rd = store.Store({'int': 'x'})

        with self.assertRaises(TypeError):
            rd.set_validator(validator)

    def test_namespaces_can_be_keys_too(self):
        d = {
            'foo': 'x',
            'foo.x.a': 1,
            'foo.x.b': 2
        }
        s = store.Store(d)
        s.set('foo', 'y')
        s.set('foo.x.a', 3)

        self.assertEqual(s.get('foo'), 'y')
        self.assertEqual(s.get_tree('foo'), {
            'x': {
                'a': 3,
                'b': 2
            }
        })

        s.delete('foo')

        with self.assertRaises(KeyError):
            s.get('foo')

        with self.assertRaises(KeyError):
            s.get_tree('foo.x.a')

        with self.assertRaises(KeyError):
            s.get_tree('foo')


class TestConfigLoader(unittest.TestCase):
    ini_str = textwrap.dedent("""
        [main]
        a = 1
        b = 2

        [subsect_a]
        c = 3
        d = 4

        [subsect_b]
        e = 5
        f = 6

        [extensions.importer.foo]
        g = 6
        h = 7

        [extensions.importer.bar]
        i = 8
        j = 9

        [extensions.downloader.zar]
        k = 10
        foo.bar = x
        """)

    ini_dict = {
        'a': '1',
        'b': '2',
        'subsect_a.c': '3',
        'subsect_a.d': '4',
        'subsect_b.e': '5',
        'subsect_b.f': '6',
        'extensions.importer.foo.g': '6',
        'extensions.importer.foo.h': '7',
        'extensions.importer.bar.i': '8',
        'extensions.importer.bar.j': '9',
        'extensions.downloader.zar.k': '10',
        'extensions.downloader.zar.foo.bar': 'x'
    }

    def test_configparser(self):
        s = store.Store()

        cp = configparser.ConfigParser()
        cp.read_string(self.ini_str)

        s.load_configparser(cp, root_sections=('main,'))
        self.assertTrue(s, self.ini_dict)

    def test_argparser(self):
        s = store.Store()

        ap = argparse.ArgumentParser()
        ap.add_argument('-i', dest='i', type=int)
        ap.add_argument('--bool', dest='bool', action='store_true')

        args = ap.parse_args(['-i', '1', '--bool'])
        s.load_arguments(args)

        self.assertEqual(s, {'i': 1, 'bool': True})


if __name__ == '__main__':
    unittest.main()
