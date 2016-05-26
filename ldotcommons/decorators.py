import collections
import functools

from .utils import get_symbol


class ArgCountError(Exception):
    pass


class VaArgs(object):
    pass


def log_call(f):
    @functools.wraps(f)
    def new_f(*args, **kw):
        method_name = f.__name__
        if isinstance(args[0], object):
            method_name = str(args[0].__class__.__name__) + '.' + method_name
        print("%s (%s, %s)" % (method_name, repr(args), repr(kw)))
        f(*args, **kw)
    return new_f


def accepts(*types):
    """ Function decorator. Checks that inputs given to decorated function
    are of the expected type.

    Parameters:
    types -- The expected types of the inputs to the decorated function.
             Must specify type for each parameter.
    """
    def info(fname, expected, actual, flag):
        """
        Convenience function returns nicely formatted error/warning msg.
        """
        format = lambda types: ', '.join([str(t).split("'")[1] for t in types])
        expected, actual = format(expected), format(actual)
        msg = "'%s' method " % fname \
              + ("accepts", "returns")[flag] + " (%s), but " % expected\
              + ("was given", "result is")[flag] + " (%s)" % actual
        return msg

    try:
        def decorator(f):
            def newf(*args):
                for i in range(0, len(types)):
                    # Check for vaargs argument
                    if types[i] == VaArgs:
                        return f(*args)
                    try:
                        arg = args[i]
                    except IndexError:
                        msg = "Invalid number of arguments: got %d expected %d"
                        raise ArgCountError(msg %
                                            (len(args), len(types)))

                    if isinstance(types[i], type):
                        if issubclass(type(arg), types[i]):
                            continue
                        else:
                            raise TypeError(info(
                                f.__name__, types, tuple(map(type, args)), 0))
                            # try:
                            #     types[i](arg)
                            #     continue
                            # except ValueError:
                            #     raise TypeError(info(
                            #         f.__name__,types, tuple(map(type, args)), 0))  # nopep8

                    elif isinstance(types[i], collections.Callable):
                        if not types[i](arg):
                            raise TypeError(info(
                                f.__name__, types, tuple(map(type, args)), 0))

                    else:
                        raise TypeError(info(
                            f.__name__, types, tuple(map(type, args)), 0))

                return f(*args)

            newf.__name__ = f.__name__
            return newf
        return decorator
    except TypeError as msg:
        raise TypeError(msg)


def symbol_loader(symbol_param, defaults=None):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if symbol_param not in kwargs:
                kwargs[symbol_param] = defaults

            if (symbol_param not in kwargs or
               not callable(kwargs[symbol_param])):
                kwargs[symbol_param] = get_symbol(
                    kwargs.get(symbol_param, defaults))

            function(*args, **kwargs)

        return wrapper

    return decorator
