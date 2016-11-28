import json
from urllib import parse, request

from ldotcommons import logging
from ldotcommons import messaging

_logger = logging.get_logger(__name__)

_ENDPOINT = 'https://api.pushover.net/1/messages.json'


class PushoverException(Exception):
    def __init__(self, *args, **kwargs):
        self.response = kwargs.pop('response')
        super(PushoverException, self).__init__(*args, **kwargs)


class Pushover(messaging.Notifier):

    def __init__(self, api_key=None, user_key=None, priority=1):
        self._api_key = api_key
        self._user_key = user_key
        self._priority = priority

    def send(self, msg, detail=''):
        data = {
            'token': self._api_key,
            'user': self._user_key,
            'message': msg,
            'priority': self._priority
        }

        if detail:
            data.update({'title': msg, 'message': detail})

        data = parse.urlencode(data).encode('utf-8')

        req = request.Request(_ENDPOINT)
        req.add_header(
            "Content-Type", "application/x-www-form-urlencoded;charset=utf-8")

        resp = request.urlopen(req, data)
        r = json.loads(resp.read().decode('utf-8'))

        if r['status'] != 1:
            raise PushoverException('Unable to send message', response=r)

        _logger.debug('Message {} send.'.format(r['request']))
