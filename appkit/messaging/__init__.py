from ldotcommons import utils

_factory = utils.Factory('ldotcommons.messaging')
_notifiers = {}


class Notifier:
    def send(self, msg, detail=''):
        raise NotImplementedError()


class Source:
    def recv(self):
        raise NotImplementedError()


class NotifierError(Exception):
    pass


def enable(name, backend, *args, **kwargs):
    if name in _notifiers:
        return
    _notifiers[name] = _factory(backend, *args, **kwargs)


def disable(name):
    del _notifiers[name]


def send(msg, detail=''):
    for n in _notifiers.values():
        n.send(msg, detail)
