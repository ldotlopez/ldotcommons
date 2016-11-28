from appkit import extension


class Meh(extension.Extension):
    __extension_name__ = 'meh'


__testapp_extensions__ = [
    Meh
]
