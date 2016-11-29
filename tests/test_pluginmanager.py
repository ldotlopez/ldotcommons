# -*- encoding: utf-8 -*-


import unittest
import sys
from os import path


from appkit import (
    exceptions,
    extension,
    extensionmanager
)


class ExtensionTypeA(extension.Extension):
    pass


class ExtensionTypeB(extension.Extension):
    pass


class ExtensionTypeC(extension.Extension):
    pass


class ExtensionA(ExtensionTypeA):
    __extension_name__ = 'ext-a'


class ExtensionB(ExtensionTypeB):
    __extension_name__ = 'ext-b'


class ExtensionC(ExtensionTypeC):
    __extension_name__ = 'ext-c'


class TestExtensionManager(unittest.TestCase):
    def test_register(self):
        em = extensionmanager.ExtensionManager('test')
        em.register_extension_point(ExtensionTypeA)
        em.register_extension_class(ExtensionA)

        e = em.get_extension_class(ExtensionTypeA, 'ext-a')
        self.assertEqual(e, ExtensionA)

    def test_register_extension_as_extension_point(self):
        em = extensionmanager.ExtensionManager('test')
        with self.assertRaises(TypeError):
            em.register_extension_point(ExtensionA)

    def test_register_already_registered_ext_point(self):
        em = extensionmanager.ExtensionManager('test')
        em.register_extension_point(ExtensionTypeA)
        with self.assertRaises(exceptions.ExtensionManagerError):
            em.register_extension_point(ExtensionTypeA)

    def test_register_subclass_of_previous_ext_point(self):
        class FooType(ExtensionTypeA):
            pass

        em = extensionmanager.ExtensionManager('test')
        em.register_extension_point(ExtensionTypeA)
        with self.assertRaises(exceptions.ExtensionManagerError):
            em.register_extension_point(FooType)

    def test_register_superclass_of_previous_ext_point(self):
        class FooType(ExtensionTypeA):
            pass

        em = extensionmanager.ExtensionManager('test')
        em.register_extension_point(FooType)
        with self.assertRaises(exceptions.ExtensionManagerError):
            em.register_extension_point(ExtensionTypeA)

    def test_register_extension_class_with_unrelated_type(self):
        em = extensionmanager.ExtensionManager('test')
        with self.assertRaises(TypeError):
            em.register_extension_class(str)

    def test_register_extension_class_with_missing_name(self):
        class NoNameExtension(extension.Extension):
            pass

        em = extensionmanager.ExtensionManager('test')
        with self.assertRaises(TypeError):
            em.register_extension_class(NoNameExtension)

    def test_register_extension_class_with_colliding_name(self):
        class FooExtension(ExtensionTypeA):
            __extension_name__ = 'xyz'

        class BarExtension(ExtensionTypeA):
            __extension_name__ = 'xyz'

        em = extensionmanager.ExtensionManager('test')
        em.register_extension_point(ExtensionTypeA)

        em.register_extension_class(FooExtension)
        with self.assertRaises(exceptions.ExtensionManagerError):
            em.register_extension_class(BarExtension)

    def test_get_extension(self):
        class Foo(extension.Extension):
            __extension_name__ = 'foo'

            def __init__(self, x):
                self.x = x

        em = extensionmanager.ExtensionManager('test')
        em.register_extension_point(extension.Extension)
        em.register_extension_class(Foo)

        e = em.get_extension(extension.Extension, 'foo', 1)
        self.assertEqual(e.x, 1)

        e = em.get_extension(extension.Extension, 'foo', 'x')
        self.assertEqual(e.x, 'x')

    def test_load_plugin(self):
        pathbck = sys.path.copy()
        pathbck.append(
            path.dirname(path.realpath(__file__)) + '/plugins/'
        )
        em = extensionmanager.ExtensionManager('testapp')
        em.register_extension_point(extension.Extension)
        em.load_plugin('meh')

        with self.assertRaises(extensionmanager.PluginNotLoadedError):
            em.load_plugin('meh2')

        sys.path = pathbck.copy()

if __name__ == '__main__':
    unittest.main()
