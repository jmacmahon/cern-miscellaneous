from __future__ import absolute_import

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from sys import stdin
from json import loads
from itertools import imap
from time import time

from json_dump import count_every

es = Elasticsearch(hosts=[{'host': 'localhost', 'port': 9198}])

def read_and_index():
    json_iter = imap(loads, count_every(stdin, 10000))
    bulk(es, json_iter, raise_on_error = True)

if __name__ == "__main__":
    read_and_index()
