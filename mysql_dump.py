from __future__ import absolute_import

import mysql.connector as mysql
from time import mktime
from json import dumps
from itertools import izip, count, imap
from contextlib import contextmanager

from json_dump import count_every

def consume(iter):
    for _ in iter:
        pass

@contextmanager
def mysql_connection(*args, **kwargs):
    connection = mysql.connect(*args, **kwargs)
    yield connection
    connection.close()


local_mysql = lambda: mysql_connection(
    user='root', password='password', host='127.0.0.1',
    database='cdsweb_custom_events')


def debug(*args, **kwargs):
    with local_mysql() as conn:
        d = Dumper(conn, *args, **kwargs)
        action = next(d.get_json())
    return action


class Dumper(object):
    """Object for dumping MySQL tables to JSON-encoded ES actions.

    Instantiate the object, and then call dump_to_file.  Might be a good idea
    for large tables to dump to a FIFO and pipe into `split` (see `man 1 split`
    for documentation)."""

    def __init__(self, connection, table, index_prefix, doc_type=None,
        suffix_format='%Y.%m', timestamp_field=None, tag=None,
        process_action=None):
        self._connection = connection
        self._table = table
        self._index_prefix = index_prefix
        self._doc_type = doc_type if doc_type is not None else table
        self._suffix_format = suffix_format
        self._timestamp_field = timestamp_field
        self._tag = tag if tag is not None else {'from_mysql': True}
        self._process_action = process_action if (process_action is not None) \
            else (lambda x: x)

        self._names = self._get_names()

    def _get_names(self):
        cursor = self._connection.cursor()
        q = 'DESC %s;' % (self._table,)
        cursor.execute(q)

        return list(imap(lambda x: x[0], cursor))

    def get_rows(self):
        cursor = self._connection.cursor()

        count_q = 'SELECT count(*) FROM %s;' % (self._table,)
        cursor.execute(count_q)
        row_count = next(cursor)[0]
        consume(cursor)

        select_q = 'SELECT * FROM %s;' % (self._table,)
        cursor.execute(select_q)

        def _inner():
            for row in cursor:
                doc = self._build_doc(row)
                action = self._build_action(doc)
                yield self._process_action(action)

        return count_every(_inner(), total=row_count)

    def get_json(self):
        return imap(self._build_json, self.get_rows())

    def dump_to_file(self, filename, flush_every=10000):
        with open(filename, 'w') as f:
            for (n, action) in izip(count(0), self.get_json()):
                if n % flush_every == 0:
                    f.flush()
                f.write(action + '\n')

    def _build_doc(self, row):
        doc = dict(zip(self._names, row))
        if self._timestamp_field is not None:
            doc['@timestamp'] = doc[self._timestamp_field]
            del doc[self._timestamp_field]

        if self._tag is not None:
            doc.update(self._tag)

        return doc

    def _build_action(self, doc):
        if '@timestamp' in doc:
            index_suffix = doc['@timestamp'].strftime(self._suffix_format)
            index = self._index_prefix + index_suffix
        else:
            index = self._index_prefix
        return {
            '_op_type': 'index',
            '_index': index,
            '_type': self._doc_type,
            '_source': doc
        }

    def _build_json(self, action):
        for key, value in action['_source'].items():
            if hasattr(value, 'timetuple'):
                action['_source'][key] = int(mktime(value.timetuple()))*1000
        return dumps(action)
