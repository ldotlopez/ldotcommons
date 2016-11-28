# -*- encoding: utf-8 -*-


import re


#
# Aliases
#


NoneType = type(None)
RegexpType = type(re.compile(r''))


#
# Metaclasses
#


class SingletonMetaclass(type):
    def __call__(cls, *args, **kwargs):  # nopep8
        instance = getattr(cls, '_instance', None)
        if not instance:
            setattr(cls,
                    '_instance',
                    super(SingletonMetaclass, cls).__call__(*args, **kwargs))
        return cls._instance


#
# Types
#

# FIXME: Null[Singleton] -> RecursiveNull[Singleton]
class Null:
    def __getattr__(self, attr):
        return Null()

    def __call__(self, *args, **kwargs):
        return Null()


class NullSingleton(Null, metaclass=SingletonMetaclass):
    def __getattr__(self, attr):
        return self

    def __call__(self, *args, **kwargs):
        return self
