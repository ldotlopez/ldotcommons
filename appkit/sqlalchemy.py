import re

import sqlalchemy as sa
from sqlalchemy import orm, event
from sqlalchemy.ext import declarative

from ldotcommons import utils


Base = declarative.declarative_base()


def _re_fn(regexp, other):
    return re.search(regexp, other, re.IGNORECASE) is not None


def create_engine(uri='sqlite:///:memory:', echo=False):
    engine = sa.create_engine(uri, echo=echo)

    # @property
    # def __monkeypatch_Base_query(self):
    #     return self.session.query(self)

    # Base.metadata.create_all(bind=engine)

    # Monkeypatch magic
    # setattr(Base, 'engine', engine)
    # setattr(Base, 'session', create_session(engine=engine))
    # setattr(Base.__class__, 'query', __monkeypatch_Base_query)

    # Enable regexp and foreign_keys functionality for sqlite connections
    if uri.startswith('sqlite:///'):
        @event.listens_for(engine, "begin")
        def do_begin(conn):
            conn.connection.create_function('regexp', 2, _re_fn)

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(conn, record):
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def create_session(uri=None, engine=None, echo=False):
    if not engine:
        engine = create_engine(uri=uri, echo=echo)

    sess = orm.sessionmaker()
    sess.configure(bind=engine)
    Base.metadata.create_all(engine)
    session = sess()

    # session = orm.scoped_session(orm.sessionmaker(bind=engine))

    return session


def query_from_params(conn, mapping, **params):

    # # This code can be used for add type-safety to this function
    # from sqlalchemy.sql import sqltypes

    # columns = self._mapping.__table__.columns
    # for (colname, column) in columns.items():
    #     columntype = column.type
    #     if isinstance(columntype, sqltypes.String):
    #         self._ops[(colname, None)] = self.by_string
    #         self._ops[(colname, 'like')] = self.by_string_like
    #         self._ops[(colname, 'regexp')] = self.by_string_regexp

    #     if isinstance(columntype, sqltypes.Integer):
    #         self._ops[(colname, 'min')] = self.by_amount_min
    #         self._ops[(colname, 'max')] = self.by_amount_max

    q = conn.query(mapping)

    for (prop, value) in params.items():
        if '_' in prop:
            key = '_'.join(prop.split('_')[:-1])
            mod = prop.split('_')[-1]
        else:
            key = prop
            mod = None

        attr = getattr(mapping, key, None)

        if mod == 'like':
            q = q.filter(attr.like(value))

        elif mod == 'regexp':
            q = q.filter(attr.op('regexp')(value))

        elif mod == 'min':
            value = utils.parse_size(value)
            q = q.filter(attr >= value)

        elif mod == 'max':
            value = utils.parse_size(value)
            q = q.filter(attr <= value)

        else:
            q = q.filter(attr == value)

    return q


def glob_to_like(x, wide=False):
    for (g, l) in (('*', '%'), ('.', '_')):
        x = x.replace(g, l)

    if wide:
        if not x.startswith('%'):
            x = '%' + x

        if not x.endswith('%'):
            x = x + '%'

    return x
