from random import choice, random, randint
from logging import getLogger, DEBUG, StreamHandler
from sys import stderr
from elasticsearch import Elasticsearch
from time import sleep

LOGGER = getLogger(__name__)
LOGGER.setLevel(DEBUG)

DELAY = 27.36
DELAY_FUZZ = 3.0

TEMPLATES = [{'mappings': {'events.downloads': {'properties': {'level': {'type': 'integer'},
     'id_bibrec': {'type': 'integer'},
     'message': {'norms': {'enabled': False},
      'type': 'string',
      'index': 'not_analyzed'},
     '@timestamp': {'type': 'date', 'format': 'dateOptionalTime'},
     'id_user': {'type': 'integer'},
     'file_version': {'type': 'short'},
     'client_host': {'type': 'ip'},
     'id_bibdoc': {'type': 'integer'},
     'file_format': {'norms': {'enabled': False},
      'type': 'string',
      'index': 'not_analyzed'}},
    '_source': {'enabled': True},
    '_ttl': {'enabled': True},
    '_all': {'enabled': False}},
   'events.pageviews': {'properties': {'id_bibrec': {'type': 'integer'},
     '@timestamp': {'type': 'date', 'format': 'dateOptionalTime'},
     'id_user': {'type': 'integer'},
     'message': {'norms': {'enabled': False},
      'type': 'string',
      'index': 'not_analyzed'},
     'client_host': {'type': 'ip'},
     'level': {'type': 'integer'}},
    '_source': {'enabled': True},
    '_ttl': {'enabled': True},
    '_all': {'enabled': False}}},
  'template': 'cds-*'},
 {'mappings': {'events.pageviews': {'properties': {'id_bibrec': {'type': 'integer'},
     '@timestamp': {'type': 'date', 'format': 'dateOptionalTime'},
     'id_user': {'type': 'integer'},
     'message': {'norms': {'enabled': False},
      'type': 'string',
      'index': 'not_analyzed'},
     'client_host': {'type': 'ip'},
     'level': {'type': 'integer'}},
    '_source': {'enabled': True},
    '_ttl': {'enabled': True},
    '_all': {'enabled': False}}},
  'template': 'cds-*'}]

def burst(es, delay=None, number=None, templates=None):
    if delay is None:
        delay = 0.2 + random() * 1.8
    if number is None:
        number = randint(1, 3)
    if templates is None:
        templates = TEMPLATES
    LOGGER.getChild('burst').info('Delay: %.1f, number: %d.', delay, number)
    for _ in xrange(number):
        es.indices.put_template(name='test-template-*', body=choice(templates))
        sleep(delay)

def multiple_bursts(es, count, delay=None, delay_fuzz=None, burst_args=None,
                    burst_kwargs=None):
    if delay is None:
        delay = DELAY
    if delay_fuzz is None:
        delay_fuzz = DELAY_FUZZ
    if burst_args is None:
        burst_args = ()
    if burst_kwargs is None:
        burst_kwargs = {}

    for _ in xrange(count):
        burst(es=es, *burst_args, **burst_kwargs)
        this_fuzz = random() * delay_fuzz * 2 - delay_fuzz
        this_delay = delay + this_fuzz
        LOGGER.getChild('multiple').info('Burst delay: %.1f.', this_delay)
        sleep(this_delay)
