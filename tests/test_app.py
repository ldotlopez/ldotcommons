import unittest

from appkit import app


class CommandExtension(app.Extension):
    __extension_name__ = 'test-command'

    def __init__(self, app, *args, **kwargs):
        super().__init__(app)
        self.args = args
        self.kwargs = kwargs


class TestExtensionManager(unittest.TestCase):
    def test_app(self):
        a = app.App('foo')
        a.register_extension_class(CommandExtension)

        e = a.get_extension('test-command', 1, 2, foo='bar', x=None)
        self.assertEqual(e.app, a)
        self.assertEqual(e.args, (1, 2))
        self.assertEqual(e.kwargs, {'foo': 'bar', 'x': None})

if __name__ == '__main__':
    unittest.main()
