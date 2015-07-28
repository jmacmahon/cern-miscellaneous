from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

es_orig = Elasticsearch([{'host': 'localhost', 'port': 9197}])
es_new = Elasticsearch([{'host': 'localhost', 'port': 9197}])

def scroll(index, new_index, size=1000):
    _id = es_orig.search(index=index,
                        scroll='1m',
                        size=size)['_scroll_id']
    finished = False

    def process_result(res):
        if new_index is not None:
            this_new_index = new_index
        else:
            this_new_index = res['_index']
        action = {
            '_op_type': 'index',
            '_index': this_new_index,
            '_type': res['_type'],
            '_source': res['_source']
        }
        return action
        
    while not finished:
        results = es_orig.scroll(scroll_id=_id,
                                scroll='1m')['hits']['hits']
        hits = map(process_result, results)
        finished = len(hits) == 0
        yield hits

def bulkbulk(scroll_gen):
    i = 0
    for hits in scroll_gen:
        bulk(es_new, hits)
        i += len(hits)
        print("Done %4d." % i)
