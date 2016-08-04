import unittest

import sys
from os import path

from appkit import extension
from appkit import extensionmanager


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
        em.register_extension_class(ExtensionA)

        e = em.get_extension_class('ext-a')
        self.assertEqual(e, ExtensionA)

    def test_register_incorrect_class(self):
        em = extensionmanager.ExtensionManager('test')
        with self.assertRaises(TypeError):
            em.register_extension_class(str)

    def test_register_missing_name(self):
        class NoNameExtension(extension.Extension):
            pass

        em = extensionmanager.ExtensionManager('test')
        with self.assertRaises(TypeError):
            em.register_extension_class(NoNameExtension)

    def test_collision(self):
        class FooExtension(ExtensionA):
            __extension_name__ = 'xyz'

        class BarExtension(ExtensionB):
            __extension_name__ = 'xyz'

        em = extensionmanager.ExtensionManager('test')
        em.register_extension_class(FooExtension)
        with self.assertRaises(ValueError):
            em.register_extension_class(BarExtension)

    def test_instances(self):
        class Foo(extension.Extension):
            __extension_name__ = 'foo'

            def __init__(self, x):
                self.x = x

        em = extensionmanager.ExtensionManager('test')
        em.register_extension_class(Foo)

        e = em.get_extension('foo', 1)
        self.assertEqual(e.x, 1)

        e = em.get_extension('foo', 'x')
        self.assertEqual(e.x, 'x')

    def test_load_plugin(self):
        pathbck = sys.path.copy()
        pathbck.append(
            path.dirname(path.realpath(__file__)) + '/plugins/'
        )
        em = extensionmanager.ExtensionManager('testapp')
        em.load_plugin('meh')

        with self.assertRaises(extensionmanager.PluginNotLoadedError):
            em.load_plugin('meh2')

        sys.path = pathbck.copy()

    # def test_same_name_no_collission(self):
    #     class ExtSubTypeA(extension.Extension):
    #         pass

    #     class ExtSubTypeB(extension.Extension):
    #         pass

    #     class ExtA(ExtSubTypeA):
    #         __extension_name__ = 'foo'

    #     class ExtB(ExtSubTypeB):
    #         __extension_name__ = 'foo'

    #     em = extensionmanager.ExtensionManager('test')
    #     em.register_extension_class(ExtA)
    #     em.register_extension_class(ExtB)

    #     self.assertEqual(
    #         em.get_extension_class('foo'),
    #         ExtA)

    #     self.assertEqual(
    #         em.get_extension_class(ExtSubTypeB, 'foo'),
    #         ExtB)

    # def test_partial_collision(self):
    #     class ExtSubTypeA(extension.Extension):
    #         pass

    #     class ExtSubTypeB(extension.Extension):
    #         pass

    #     class ExtSubTypeC(extension.Extension):
    #         pass

    #     class Ext1(ExtSubTypeA, ExtSubTypeB):
    #         __extension_name__ = 'foo'

    #     class Ext2(ExtSubTypeB, ExtSubTypeC):
    #         __extension_name__ = 'foo'

    #     em = extensionmanager.ExtensionManager('test')
    #     em.register_extension_class(Ext1)
    #     with self.assertRaises(ValueError):
    #         em.register_extension_class(Ext2)

if __name__ == '__main__':
    unittest.main()
