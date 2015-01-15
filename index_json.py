from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from sys import stdin
from json import loads
from itertools import imap

es = Elasticsearch(hosts=[{'host': 'localhost', 'port': 9197}])

def count_every(iterable, n=10000):
    ii = 0
    for elem in iterable:
        if ii % n == 0:
            print('Done %d' % ii)
        ii += 1
        yield elem

def read_and_index():
    json_iter = imap(loads, count_every(stdin, 10000))
    bulk(es, json_iter, raise_on_error = True)

if __name__ == "__main__":
    read_and_index()
