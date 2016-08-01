from datetime import datetime
import email
import imaplib
from itertools import chain
import mailbox
import time

# from ldotcommons import messaging


def email_date_to_native(dt):
    dt = email.utils.parsedate(dt)
    dt = time.mktime(dt)
    return datetime.fromtimestamp(dt)


def email_newer_than(email, max_age, now=datetime.now()):
        dt = email_date_to_native(email['date'])
        delta = now - dt

        return delta.total_seconds() <= (60*60*24*max_age)


def imap_query_uids(M, query):
    if not query:
        query = 'ALL'

    typ, data = M.search(None, query)
    assert typ == 'OK'
    return data[0].split()


def imap_fetch(M, uid, flags_mod, flags):
    resp, data = M.fetch(uid, '(RFC822)')
    assert resp == 'OK'

    if flags_mod:
        M.store(uid, flags_mod, flags)

    return email.message_from_bytes(data[0][1])


def imap_recv(M, max_age, now=datetime.now()):
    messages = []
    for (query, flags_mod, flags) in (
            ('(SEEN)', None, None),
            ('(UNSEEN)', r'-FLAGS', r'\SEEN')
            ):

        uids = map(lambda x: int(x), imap_query_uids(M, query))
        uids = reversed(sorted(uids))
        uids = map(lambda x: bytes(str(x).encode('ascii')), uids)

        for uid in uids:
            msg = imap_fetch(M, uid, flags_mod, flags)
            if email_newer_than(msg, max_age, now=now):
                messages.append(msg)
            else:
                break

    return sorted(messages,
                  key=lambda x: email_date_to_native(x['date']),
                  reverse=True)


class ImapFolder:
    def __init__(self,
                 host=None, port=993,
                 username=None, password=None, ssl=True,
                 folder='INBOX',
                 mbox_paths=[],
                 max_age=60, now=None
                 ):

        if isinstance(mbox_paths, str):
            mbox_paths = [mbox_paths]

        if host:
            if not username or not password:
                raise Exception('No credentials provided')

            self._opts = {
                'host': host,
                'port': port,
                'username': username,
                'password': password,
                'port': port,
                'folder': folder,
            }
            self._m_cls = imaplib.IMAP4_SSL if ssl else imaplib.IMAP4

        elif mbox_paths:
            self._opts = {
                'mboxes': mbox_paths
            }
            self._m_cls = None

        else:
            raise("Neither host or mbox_path specified")

        self._now = now or datetime.now()
        self._max_age = max_age

    def recv(self, flatten=True):
        if self._m_cls:
            M = self._m_cls(
                self._opts['host'],
                self._opts['port'])
            M.login(
                self._opts['username'],
                self._opts['password'])
            M.select(self._opts['folder'])

            messages = imap_recv(M, max_age=self._max_age, now=self._now)

        else:
            messages = [x for x in
                        chain.from_iterable([mailbox.mbox(mbox).values()
                                             for mbox in self._opts['mboxes']])
                        ]

        for m in chain.from_iterable([m.walk() for m in messages]):
            payload_ = m.get_payload(decode=True)

            # Multipart messages doesn't have payload
            if payload_ is None:
                continue

            encodings = ['utf-8', 'iso-8859-15', 'ascii']
            msg_encoding = m.get_content_charset()
            if msg_encoding:
                encodings = [msg_encoding.split(',')[0]] + encodings

            payload = None
            for encoding in encodings:
                try:
                    payload = payload_.decode(encoding)
                    m.set_payload(payload, charset=encoding)
                    break
                except UnicodeDecodeError:
                    pass

            if payload is None:
                print("Unable to decode")
                continue

        if flatten:

            # Copy headers from parent message to its children
            for message in messages:
                for m in message.walk():
                    message_keys = set(message.keys())
                    m_keys = set(m.keys())
                    for k in message_keys - m_keys:
                        m[k] = message[k]

            # Flat list
            messages = [m for m in chain.from_iterable(
                [m.walk() for m in messages]) if not m.is_multipart()]

        # for message in messages:
        #     for m in message.walk():
        #         print("multipart: {}, payload: {}".format(
        #             m.is_multipart(), type(m.get_payload())))

        return messages

    # @property
    # def messages(self):
    #     if self._messages is None and self._M:
    #         self._messages = self._fetch()

    #     return self._messages

    # @messages.setter
    # def messages(self, value):
    #     raise ValueError('read-only property')

    # def walk_messages(self):
    #     return chain.from_iterable([m.walk() for m in self.messages])

    # def _fetch(self):
    #     def _search(self, query=None):
    #         if not query:
    #             query = 'ALL'

    #         typ, data = self._M.search(None, query)
    #         assert typ == 'OK'
    #         uids = data[0].split()
    #         for uid in reversed(uids):
    #             yield uid

    #     def email_date_to_native(date):
    #             date = email.utils.parsedate(date)
    #             date = time.mktime(date)
    #             return datetime.fromtimestamp(date)

    #     def _is_recent(msg):
    #         date = email_date_to_native(msg['date'])
    #         delta = self._now - date

    #         return delta.total_seconds() <= (60*60*24*self._max_age)

    #     msgs = []

    #     for search, flag_mod, flags in [
    #         ('(SEEN)', None, None),
    #         ('(UNSEEN)', '-FLAGS', r'\SEEN')
    #     ]:
    #         for uid in _search(search):
    #             resp, data = self._M.fetch(uid, '(RFC822)')
    #             msg = self.read_message_from_bytes(data[0][1])

    #             if flag_mod:
    #                 self._M.store(uid, flag_mod, flags)

    #             if _is_recent(msg):
    #                 msgs.append(msg)
    #             else:
    #                 break

    # def read_message_from_file(self, path):
    #     with open(path, 'rb') as fh:
    #         self.read_message_from_bytes(fh.read())

    # def read_message_from_bytes(self, buff):
    #     msg = email.message_from_bytes(buff)
    #     for m in msg.walk():
    #         payload_ = m.get_payload(decode=True)

    #         # Multipart messages doesn't have payload
    #         if payload_ is None:
    #             continue

    #         encodings = ['utf-8', 'iso-8859-15', 'ascii']
    #         msg_encoding = m.get_content_charset()
    #         if msg_encoding:
    #             encodings = [msg_encoding] + encodings

    #         payload = None
    #         for encoding in encodings:
    #             try:
    #                 payload = payload_.decode(encoding)
    #                 m.set_payload(payload, charset=encoding)
    #                 break
    #             except UnicodeDecodeError:
    #                 pass

    #         if payload is None:
    #             print("Unable to decode")
    #             continue

    #     self._messages.append(msg)

    # def process_with(self, inspector):
    #     for msg in self.messages:
    #         ret = inspector.process(msg)
    #         if ret is None:
    #             continue

    #         elif isinstance(ret, collections.Iterable):
    #             for r in ret:
    #                 yield r
    #         else:
    #             yield ret

    #     raise StopIteration()
