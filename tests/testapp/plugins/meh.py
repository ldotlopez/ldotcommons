from appkit.extensionmanager import Extension


class Meh(Extension):
    __extension_name__ = 'meh'


__testapp_extensions__ = [
    Meh
]
