import unittest
from ldotcommons.utils import (
    InmutableDict,
    parse_size,
    parse_interval,
    parse_date
)


class TestInmutableDict(unittest.TestCase):
    def test_assing(self):
        x = InmutableDict()
        with self.assertRaises(TypeError):
            x['a'] = 1

    def test_kwinit(self):
        x = InmutableDict(a=1)
        self.assertEqual(x['a'], 1)

    def test_pop(self):
        x = InmutableDict(a=1)
        with self.assertRaises(TypeError):
            x.pop('a')

    def test_clear(self):
        x = InmutableDict(a=1)
        with self.assertRaises(TypeError):
            x.clear()

    def test_subclass(self):
        class X(InmutableDict):
            def __init__(self, **kwargs):
                kwargs = {str(k) + str(k): v for (k, v) in kwargs.items()}
                super().__init__(**kwargs)

        x = X(foo=1, bar=2)
        self.assertEqual(x['foofoo'], 1)
        with self.assertRaises(TypeError):
            x['foo'] = 3


class TestParseSize(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(parse_size('8'), 8)
        self.assertEqual(parse_size('1234'), 1234)
        self.assertEqual(parse_size('1.2'), 1.2)
        self.assertEqual(parse_size('1,32'), 1.32)
        self.assertNotEqual(parse_size('7'), 8)

    def test_invalid_values(self):
        with self.assertRaises(ValueError):
            parse_size('x')

        with self.assertRaises(ValueError):
            parse_size('1w')

        with self.assertRaises(ValueError):
            parse_size('1x1')

    def test_suffixes(self):
        self.assertEqual(parse_size('1k'), 1*10**3)
        self.assertEqual(parse_size('2 K'), 2*10**3)
        self.assertEqual(parse_size('3 m'), 3*10**6)
        self.assertEqual(parse_size('4M'), 4*10**6)
        self.assertEqual(parse_size('5g'), 5*10**9)
        self.assertEqual(parse_size('6 G'), 6*10**9)
        self.assertEqual(parse_size('7 t'), 7*10**12)
        self.assertEqual(parse_size('8T'), 8*10**12)
        self.assertEqual(parse_size('9p'), 9*10**15)
        self.assertEqual(parse_size('10 P'), 10*10**15)
        self.assertEqual(parse_size('11 e'), 11*10**18)
        self.assertEqual(parse_size('12E'), 12*10**18)
        self.assertEqual(parse_size('13z'), 13*10**21)
        self.assertEqual(parse_size('14 Z'), 14*10**21)
        self.assertEqual(parse_size('15 y'), 15*10**24)
        self.assertEqual(parse_size('16Y'), 16*10**24)
        self.assertEqual(parse_size('1.2 Mb'), 1.2*10**6)
        self.assertEqual(parse_size('1,2Gb'), 1.2*10**9)


class TestTimeParsing(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(parse_interval('1'), 1)
        self.assertNotEqual(parse_interval('2'), 1)

    def test_invalid_values(self):
        with self.assertRaises(ValueError):
            parse_interval('1.1')

        with self.assertRaises(ValueError):
            parse_interval('1,1')

        with self.assertRaises(ValueError):
            parse_interval('x')

        with self.assertRaises(ValueError):
            parse_interval('18Z')

        with self.assertRaises(ValueError):
            parse_interval('1h 18m')

    def test_suffixes(self):
        # Seconds
        self.assertEqual(parse_interval('1S'), 1)
        self.assertEqual(parse_interval('2   S'), 2)  # multiple spaces here ;)
        with self.assertRaises(ValueError):
            parse_interval('1s')
        with self.assertRaises(ValueError):
            parse_interval('1 s')

        # Minutes
        self.assertEqual(parse_interval('3M'), 3*60)
        self.assertEqual(parse_interval('4 M'), 4*60)

        # Hours
        self.assertEqual(parse_interval('5H'), 5*60*60)
        self.assertEqual(parse_interval('6    H'), 6*60*60)
        with self.assertRaises(ValueError):
            parse_interval('7 h')
        with self.assertRaises(ValueError):
            parse_interval('8h')

        # days
        self.assertEqual(parse_interval('8d'), 8*60*60*24)
        self.assertEqual(parse_interval('2  d'), 2*60*60*24)
        with self.assertRaises(ValueError):
            parse_interval('1D')
        with self.assertRaises(ValueError):
            parse_interval('1 D')

        # months
        self.assertEqual(parse_interval('3m'), 3*60*60*24*30)
        self.assertEqual(parse_interval('4 m'), 4*60*60*24*30)

        # years
        self.assertEqual(parse_interval('8y'), 8*60*60*24*365)
        self.assertEqual(parse_interval('2  y'), 2*60*60*24*365)
        with self.assertRaises(ValueError):
            parse_interval('1Y')
        with self.assertRaises(ValueError):
            parse_interval('1 Y')


class DateParsingTest(unittest.TestCase):
    def test_yyyyymmdd(self):
        tests = [
            ('1969-07-20 12:34', -14214360),
            ('2015/04/01', 1427839200),
            ('2015 12', 1448924400),
        ]
        for (s, i) in tests:
            self.assertEqual(parse_date(s), i, s)


if __name__ == '__main__':
    unittest.main()
