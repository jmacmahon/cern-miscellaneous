from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from sys import stdin
from json import loads
from itertools import imap
from time import time

es = Elasticsearch(hosts=[{'host': 'localhost', 'port': 9198}])

def count_every(iterable, n=10000):
    ii = 0
    start_t = t = time()
    for elem in iterable:
        if ii % n == 0:
            new_t = time()
            dt_total = float(new_t - start_t)
            ditems_dt_avg = float(ii)/dt_total
            dt_block = float(new_t - t)
            ditems_dt_block = float(n)/dt_block
            t = new_t
            print('Done %d in %.1fs (average: %.1f/s, block: %.1f/s)' %
                  (ii, dt_total, ditems_dt_avg, ditems_dt_block))
        ii += 1
        yield elem

def read_and_index():
    json_iter = imap(loads, count_every(stdin, 10000))
    bulk(es, json_iter, raise_on_error = True)

if __name__ == "__main__":
    read_and_index()
