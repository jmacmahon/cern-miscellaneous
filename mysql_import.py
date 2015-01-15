import mysql.connector as mysql
from datetime import datetime
from time import sleep, mktime
from json import dumps
from itertools import izip, count, imap

from elasticsearch import Elasticsearch, ConnectionError
from elasticsearch.helpers import streaming_bulk, bulk, BulkIndexError

import logging
import sys
logging.getLogger('elasticsearch').addHandler(logging.StreamHandler(
    stream = sys.stderr
))

es = Elasticsearch(
    hosts = [{
        "host": "localhost",
        "port": 9197
    }]
)

INVENIO_PREFIX = "cds-"
CHUNK_SIZE = 500
LAST_CHUNK = None
FAILED_CHUNKS = []

def fetch_and_index(conn, time_from, time_to):
    global LAST_CHUNK, FAILED_CHUNKS
    failed_chunks = []

    downloads_errors = []
    print('Running downloads query.')
    downloads_iterator = run_downloads_query(conn, time_from, time_to)
    finished = False
    while not finished:
        print('Starting bulk index...')
        try:
            dls_result = bulk(es, downloads_iterator, raise_on_error=True)
        except BulkIndexError as e:
            downloads_errors.append(e)
        except ConnectionError as e:
            downloads_errors.append(e)
            FAILED_CHUNKS.append(LAST_CHUNK)
            LAST_CHUNK = []
            print('Failed. Sleeping for 60s...')
            sleep(60)
        else:
            finished = True

    pageviews_errors = []
    print('Running pageviews query.')
    pageviews_iterator = run_pageviews_query(conn, time_from, time_to)
    print('Starting bulk index...')
    
    finished = False
    while not finished:
        print('Starting bulk index...')
        try:
            pvs_result = bulk(es, downloads_iterator, raise_on_error=True)
        except BulkIndexError as e:
            pageviews_errors.append(e)
        except ConnectionError as e:
            pageviews_errors.append(e)
            FAILED_CHUNKS.append(LAST_CHUNK)
            LAST_CHUNK = []
            print('Failed. Sleeping for 60s...')
            sleep(60)
        else:
            finished = True

    return ((downloads_errors, dls_result), (pageviews_errors, pvs_result))
    
    
def with_myql(f, *args, **kwargs):
    connection = mysql.connect(user = 'root', password = 'password',
        host = '127.0.0.1', database = 'cdsweb_before_2014_12_08_elasticsearch')
    try:
        ret = f(connection, *args, **kwargs)
    except Exception as e:
        connection.close()
        raise e
    return (ret, connection)

def dump_remainder(connection, time_from, time_to, modulus=1000000):
    downloads_json = imap(dump_action, run_downloads_query(connection, time_from, time_to))
    downloads_buffer = []
    for (n, action) in izip(count(0), downloads_json):
        if n % modulus == 0:
            downloads_buffer = []
        downloads_buffer.append(action)
    with open('/home/joe/elasticsearch/downloads_remainder.json', 'w') as f:
        f.writelines(downloads_buffer)

    pageviews_json = imap(dump_action, run_pageviews_query(connection, time_from, time_to))
    pageviews_buffer = []
    for (n, action) in izip(count(0), pageviews_json):
        if n % modulus == 0:
            pageviews_buffer = []
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
        global LAST_CHUNK
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

            if ii % CHUNK_SIZE == 0:
                LAST_CHUNK = []

            ii += 1
            if ii % 10000 == 0:
                print('Pageviews row: %4d0k.' % (ii / 10000))

            LAST_CHUNK.append(action)
            yield action

    return pageviews(cursor)

def run_downloads_query(conn, time_from, time_to):
    cursor = conn.cursor()
    query = "SELECT * FROM rnkDOWNLOADS WHERE download_time" \
        " BETWEEN %s AND %s;"
    cursor.execute(query, (time_from, time_to))

    def downloads(cursor):
        global LAST_CHUNK
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

            if ii % CHUNK_SIZE == 0:
                LAST_CHUNK = []

            ii += 1
            if ii % 10000 == 0:
                print('Downloads row: %4d0k.' % (ii / 10000))

            LAST_CHUNK.append(action)
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

def create_new_index(suffix):
    index_name = INVENIO_PREFIX + suffix
    if not es.indices.exists(index = [index_name]):
        es.indices.create(
            index = index_name,
            #body = INVENIO_INDEX_META
        )

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
