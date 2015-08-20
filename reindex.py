from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from itertools import imap
from geoip import geolite2

from json_dump import count_every, scroll

es_orig = Elasticsearch([{'host': 'localhost', 'port': 9197}])
es_new = Elasticsearch([{'host': 'localhost', 'port': 9197}])

def process_and_bulk(scroll_gen, processor=None):
    if processor is None:
        processor = lambda x: x
    processed = imap(processor, scroll_gen)

    bulk(es_new, processed)

def test_processor(action):
    action['_source']['test'] = 1
    return action
def undo_test_processor(action):
    if 'test' in action['_source']:
        del action['_source']['test']
    return action

def geoip_processor(field):
    def _inner(action):
        ip_data = geolite2.lookup(action['_source'][field])
        if ip_data is not None:
            if 'geoip' not in action['_source']:
                action['_source']['geoip'] = {}
            if ip_data.country is not None:
                action['_source']['geoip']['country_code2'] = ip_data.country
            if ip_data.location is not None:
                action['_source']['geoip']['location'] = {
                    'lat': ip_data.location[0],
                    'lon': ip_data.location[1]
                }
        return action
    return _inner
