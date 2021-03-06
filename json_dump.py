from elasticsearch import Elasticsearch
from json import dumps
from itertools import imap
from time import time

es = Elasticsearch([{'host': 'localhost', 'port': 9197}])

def count_every(iterable, n=10000, total=None):
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

            if total is not None:
                percentage = 100 * float(ii)/total
                try:
                    eta = (total - ii)/ditems_dt_avg
                except ZeroDivisionError:
                    eta = 0
                print('Completion: %.1f%%; ETA: %.0fs' % (percentage, eta))
        ii += 1
        yield elem

def scroll(es, index, size=10000, **kwargs):
    initial_query_raw = es.search(index=index,
                                  scroll='1m',
                                  size=size,
                                  **kwargs)
    _id = initial_query_raw['_scroll_id']

    def process_result(res):
        try:
            action = {
                '_op_type': 'index',
                '_index': res['_index'],
                '_type': res['_type'],
                '_source': res['_source'],
                '_id': res['_id']
            }
        except KeyError:
            print(repr(res))
            raise
        return action

    for res in initial_query_raw['hits']['hits']:
        yield process_result(res)

    finished = False
    while not finished:
        results = es.scroll(scroll_id=_id,
                            scroll='1m')['hits']['hits']
        finished = len(results) == 0
        for res in results:
            yield process_result(res)

def file_dump(scroll_gen, filename='dump.json'):
    json_dump = imap(lambda rec: dumps(rec) + '\n', scroll_gen)
    with open(filename, 'a') as dump:
        dump.writelines(json_dump)
