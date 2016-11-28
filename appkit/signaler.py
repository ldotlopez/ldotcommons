# -*- coding: utf-8 -*-

import blinker


class _BaseException(Exception):
    pass


class SignalRegisterError(_BaseException):
    def __init__(self, signal, message):
        self.signal = signal
        self.message = message
        super().__init__()


class UnknowSignalError(_BaseException):
    def __init__(self, signal, message):
        self.signal = signal
        super().__init__()


class Signaler:
    def __init__(self):
        self._signals = {}

    @property
    def signals(self):
        return list(self._signals.keys())

    def get_signal(self, name):
        if name not in self._signals:
            raise UnknowSignalError(name)

        return self._signals[name]

    def register(self, name):
        if name in self._signals:
            msg = "Signal '{name}' was already registered"
            msg = msg.format(name=name)
            raise SignalRegisterError(name, message=msg)

        ret = blinker.Signal()
        self._signals[name] = ret

        return ret

    def connect(self, name, call, **kwargs):
        self.get_signal(name).connect(call, **kwargs)

    def disconnect(self, name, call, **kwargs):
        self.get_signal(name).disconnect(call, **kwargs)

    def send(self, name, **kwargs):
        self.get_signal(name).send(**kwargs)
