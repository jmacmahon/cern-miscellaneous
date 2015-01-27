import mysql.connector as mysql
from time import mktime
from json import dumps
from itertools import izip, count, imap
from contextlib import contextmanager

INVENIO_PREFIX = "cds-"

@contextmanager
def mysql_connection(*args, **kwargs):
    connection = mysql.connect(*args, **kwargs)
    yield connection
    connection.close()

local_mysql = lambda: mysql_connection(
    user='root', password='password', host='127.0.0.1',
    database='cdsweb_before_2014_12_08_elasticsearch')

def len_iter(iter_):
    return sum(1 for _ in iter_)

def dump_remainder(connection, time_from, time_to, modulus=1000000):
    downloads_json = imap(dump_action, run_downloads_query(connection, time_from, time_to))
    downloads_buffer = []
    for (n, action) in izip(count(0), downloads_json):
        if n % modulus == 0:
            downloads_buffer = []
            print('Reset at n = %d.' % n)
        downloads_buffer.append(action)
    with open('/home/joe/elasticsearch/downloads_remainder.json', 'w') as f:
        f.writelines(downloads_buffer)

    pageviews_json = imap(dump_action, run_pageviews_query(connection, time_from, time_to))
    pageviews_buffer = []
    for (n, action) in izip(count(0), pageviews_json):
        if n % modulus == 0:
            pageviews_buffer = []
            print('Reset at n = %d.', n)
        pageviews_buffer.append(action)
    with open('/home/joe/elasticsearch/pageviews_remainder.json', 'w') as f:
        f.writelines(pageviews_buffer)

def dump_to_files(connection, time_from, time_to):
    downloads_json = imap(dump_action, run_downloads_query(connection, time_from, time_to))
    with open('/home/joe/elasticsearch/downloads.json', 'w') as f:
        for (n, action) in izip(count(0), downloads_json):
            if n % 10000 == 0:
                f.flush()
            f.write(action + '\n')

    pageviews_json = imap(dump_action, run_pageviews_query(connection, time_from, time_to))
    with open('/home/joe/elasticsearch/pageviews.json', 'w') as f:
        for (n, action) in izip(count(0), pageviews_json):
            if n % 10000 == 0:
                f.flush()
            f.write(action + '\n')

def dump_action(action):
    action['_source']['@timestamp'] = int(mktime(action['_source']['@timestamp'].timetuple()))*1000
    return dumps(action)

def run_pageviews_query(conn, time_from, time_to):
    cursor = conn.cursor()
    query = "SELECT * FROM rnkPAGEVIEWS WHERE view_time" \
        " BETWEEN %s AND %s;"
    cursor.execute(query, (time_from, time_to))

    def pageviews(cursor):
        ii = 0
        for row in cursor:
            doc = build_doc_from_pageview_row(row)
            index_suffix = doc['@timestamp'].strftime('%Y')
            if index_suffix == "2014":
                index_suffix = "olddata-2014"
            action = {
                "_op_type": "index",
                "_index": INVENIO_PREFIX + index_suffix,
                "_type": doc['type']
            }
            del doc['type']
            action['_source'] = doc

            ii += 1
            if ii % 10000 == 0:
                print('Pageviews row: %4d0k.' % (ii / 10000))

            yield action

    return pageviews(cursor)

def run_downloads_query(conn, time_from, time_to):
    cursor = conn.cursor()
    query = "SELECT * FROM rnkDOWNLOADS WHERE download_time" \
        " BETWEEN %s AND %s;"
    cursor.execute(query, (time_from, time_to))

    def downloads(cursor):
        ii = 0
        for row in cursor:
            doc = build_doc_from_download_row(row)
            index_suffix = doc['@timestamp'].strftime('%Y')
            if index_suffix == "2014":
                index_suffix = "olddata-2014"
            action = {
                "_op_type": "index",
                "_index": INVENIO_PREFIX + index_suffix,
                "_type": doc['type'],
            }
            del doc['type']
            action['_source'] = doc

            ii += 1
            if ii % 10000 == 0:
                print('Downloads row: %4d0k.' % (ii / 10000))

            yield action
                
    return downloads(cursor)

def build_doc_from_pageview_row(row):
    doc = {
        "id_bibrec": row[0],
        "id_user": row[1],
        "@timestamp": row[3],
        "type": "events.pageviews"
    }
    try:
        ip = ipv4_from_int(row[2])
        if ip is not None:
            doc['client_host'] = ip
    except TypeError:
        pass
    return doc
        
def build_doc_from_download_row(row):
    doc = {
        "id_bibrec": row[0],
        "@timestamp": row[1],
        "id_user": row[3],
        "id_bibdoc": row[4],
        "file_version": row[5],
        "file_format": row[6],
        "type": "events.downloads"
    }
    try:
        ip = ipv4_from_int(row[2])
        if ip is not None:
            doc['client_host'] = ip
    except TypeError:
        pass
    return doc

def ipv4_from_int(the_int):
    if not (the_int & 0x00000000) == 0:
        return None
    octets = (
        (the_int & 0xFF000000) >> 24,
        (the_int & 0x00FF0000) >> 16,
        (the_int & 0x0000FF00) >> 8,
        (the_int & 0x000000FF)
    )
    return "%d.%d.%d.%d" % octets
