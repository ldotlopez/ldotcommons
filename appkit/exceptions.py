# -*- encoding: utf-8 -*-


import builtins


class Exception(builtins.Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        for (k, v) in kwargs.items():
            if hasattr(self, k):
                msg = (
                    "Invalid argument: '{arg}' "
                    "(already present in base Exception)"
                )
                msg = msg.format(arg=k)
                raise TypeError(msg)

            setattr(self, k, v)


class ExtensionManagerError(Exception):
    pass
