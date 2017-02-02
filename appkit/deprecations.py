import functools
import warnings


class DeprecatedClass:
    def __init__(self, *args, **kwargs):
        warnings.warn("Deprecated class: {}".format(
            self.__class__.__name__))
        super().__init__(*args, **kwargs)


def deprecatedmethod(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        warnings.warn('Deprecated method: {}'.format(
            f.__name__))
        return f(*args, **kwargs)

    return wrapped
