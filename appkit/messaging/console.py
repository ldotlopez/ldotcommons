from ldotcommons import logging
from ldotcommons import messaging
from ldotcommons import utils


class Console(messaging.Notifier):
    def __init__(self, prog=utils.prog_name(), line_len=72):
        self._logger = logging.get_logger(prog)
        self._line_len = line_len

    def send(self, msg, detail=''):
        self._logger.info('- {}'.format(msg))
        for line in detail.split('\n'):
            for chunk in [line[i:i+self._line_len] for i in range(0, len(line), self._line_len)]:
                self._logger.info('  {}'.format(chunk))
