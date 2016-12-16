import unittest

from appkit import app


class TestExtension(app.Extension):
    __extension_name__ = 'test'

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class ServiceExtension(app.Extension):
    __extension_name__ = 'test-service'

    def __init__(self, app):
        super().__init__(app)
        self.i = 0

    def incr(self):
        self.i += 1


class TestExtensionManager(unittest.TestCase):
    def test_app(self):
        a = app.BaseApp('foo')
        a.register_extension_point(app.Extension)
        a.register_extension_class(TestExtension)

        e = a.get_extension(app.Extension, 'test', 1, 2, foo='bar', x=None)
        self.assertEqual(e.args, (1, 2))
        self.assertEqual(e.kwargs, {'foo': 'bar', 'x': None})


class TestApp(unittest.TestCase):
    def test_service_app(self):
        class FooApp(app.ServiceAppMixin, app.BaseApp):
            def __init__(self, name):
                app.BaseApp.__init__(self, name)
                app.ServiceAppMixin.__init__(self)

        class FooService(app.Service):
            __extension_name__ = 'test'

            def __init__(self, app, x=0):
                super().__init__(app)
                self._x = x

            @property
            def x(self):
                ret = self._x
                self._x += 1
                return ret

        a = FooApp('test')
        a.register_extension_class(FooService)

        self.assertEqual(
            a.get_extension(app.Service, 'test').x,
            0)
        self.assertEqual(
            a.get_extension(app.Service, 'test').x,
            1)

    def test_command_line_app(self):
        class TestCommand(app.Command):
            __extension_name__ = 'foo'

            arguments = [
                app.cliargument('nums', nargs='+')
            ]

            def run(args):
                return sum([int(x) for x in args.nums])

        class TestApp(app.CommandlineAppMixin, app.BaseApp):
            pass

        a = TestApp('foo')
        a.register_extension_class(TestCommand)

        self.assertEqual(
            a.run('1', '2', '3'),
            6)

if __name__ == '__main__':
    unittest.main()
