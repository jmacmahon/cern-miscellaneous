# -*- coding: utf-8 -*-

from datetime import datetime
from time import time, sleep
from elasticsearch import Elasticsearch
from random import randint
from math import sqrt
import json

es = Elasticsearch(
#    hosts = ['dls-joe-test01'],
#    hosts = [{
#        "host": 'dls-joe-test03.cern.ch',
#        "port": 443,
#        "http_auth": ('elasticsearch', 'elasticsearch'),
#        "use_ssl": True
#    }]
    hosts = [{
        "host": "localhost",
        "port": 9199
    }]
)

DOCUMENT = {
    "message" : "132.248.12.54 - - [01/Mar/2013:22:21:43 +0100] \"GET /MathJax/fonts/HTML-CSS/TeX/otf/MathJax_Main-Regular.otf HTTP/1.1\" 200 41876 \"http://cds.cern.ch/search?ln=en&cc=CERN+Bookshop&sc=1&p=power+of+alpha&f=title&action_search=Search\" \"Mozilla/5.0 (Windows NT 5.1; rv:19.0) Gecko/20100101 Firefox/19.0\" 1092571",
    "@timestamp" : "2013-03-01T21:21:43.000Z",
    "clientip" : "132.248.12.54",
    "verb" : "GET",
    "request" : "/MathJax/fonts/HTML-CSS/TeX/otf/MathJax_Main-Regular.otf",
    "response" : "200",
    "bytes" : 41876,
    "referrer" : "\"http://cds.cern.ch/search?ln=en&cc=CERN+Bookshop&sc=1&p=power+of+alpha&f=title&action_search=Search\"",
    "agent" : "\"Mozilla/5.0 (Windows NT 5.1; rv:19.0) Gecko/20100101 Firefox/19.0\"",
    "timetaken" : 1092571,
    "geoip" : {
        "country_code2" : "MX",
        "continent_code" : "NA",
        "region_name" : "09",
        "city_name" : "Mexico",
        "timezone" : "America/Mexico_City",
        "location" : [
            -99.1386,
            19.434200000000004
        ]
    },
    "type" : "apachelog"
}

INDEX = "benchmark"
TYPE = "apachelog"
TIME = datetime(2012, 7, 4, 8, 0) # Python's datetime is timezone naïve

document_no_timestamp = DOCUMENT.copy()
del document_no_timestamp['@timestamp']

def insert_singular(_):
    es.index(index = INDEX, doc_type = TYPE, body = DOCUMENT)

def insert_seq_timestamp(block_size, block_number, offset):
    this_document = DOCUMENT.copy()
    this_document['@timestamp'] = datetime.strftime(datetime.fromtimestamp(
        1362092400 + (block_size * block_number + offset)),
        '%Y-%m-%dT%H:%M:%S.000Z'
    )
    es.index(index = INDEX, doc_type = TYPE, body = this_document)

def benchmark_f(f, n = 1000):
    start_time = time()
    print("%d iterations of %s:" % (n, str(f)))
    ii = 0
    while ii < n:
        f(ii)
        ii += 1
    end_time = time()
    d_time = end_time - start_time
    rate = float(n) / d_time
    print("Took %f.2 s, rate = %f.2 /s" % (d_time, rate))

def query_f(interval = 'day'):
    return {
    'aggregations': {
        'time': {
            'date_histogram': {
                'field': '@timestamp',
                'interval': interval,
                'order': {
                    '_count': 'asc'
                }
            }
        }
    }
}

def run_query(interval = 'day', timeout = 30, index = INDEX):
    raw_response = es.search(index = index, body = query_f(interval), \
                           search_type = 'count', request_timeout = timeout)
    return raw_response

def distribution(raw_response, percentile_boundaries = \
                 [0, 0.05, 0.5, 0.95, 1.0]):
    buckets = raw_response['aggregations']['time']['buckets']
    
    squares_total = 0
    for value in buckets:
        squares_total += value['doc_count'] ** 2
    total = raw_response['hits']['total']

    n = len(buckets)
    mu = float(total) / float(n)
    var = float(squares_total) / float(n) - (mu ** 2)
    sigma = sqrt(var)
    
    percentiles = {}
    for pc in percentile_boundaries:
        pc_index = int(round(pc * (n-1)))
        percentiles[pc] = buckets[pc_index]['doc_count']

    return (n, mu, sigma, percentiles)

def benchmark_shard():
    data = {}
    ii = 1
    while True:
        start_time = time()
        r = run_query('1s')
        d_time = time() - start_time
        n = distribution(r, [])[0]
        print('Took %.2fs.  New n = %d.' % (d_time, n))

        es.index(index = "benchmark_data", doc_type = "query_time_log", body = {
            "type": "query_time_log",
            "number_of_indices": n,
            "time_taken": d_time
        })
        """
        if n not in data:
            data[n] = []
        data[n].append(d_time)

        if ii == 0:
            with open('data.json', 'w') as ff:
                json.dump(data, ff)
        ii = (ii + 1) % 10
        """
        sleep(0.5)
            
if __name__ == '__main__':
    pass
