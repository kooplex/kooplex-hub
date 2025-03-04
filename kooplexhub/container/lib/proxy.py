"""
@author: David Visontai, Jozsef Steger
"""
import os
import json
import requests
import logging

try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

KOOPLEX['proxy'].update({})

logger = logging.getLogger(__name__)

def getroutes():
    url = os.path.join(KOOPLEX['proxy'].get('url_api', 'http://localhost:8001/api'), 'routes')
    headers = {'Authorization': 'token %s' % KOOPLEX['proxy'].get('auth_token', '') }
    return requests.get(url, headers=headres)


def droproutes():
    resp = getroutes()
    routes = json.loads(resp.content.decode())
    headers = {'Authorization': 'token %s' % KOOPLEX['proxy'].get('auth_token', '') }
    for r, v in routes.items():
        url = os.path.join(KOOPLEX['proxy'].get('url_api', 'http://localhost:8001/api'), 'routes', r[1:])
        requests.delete(url, headers=headers)
        logging.debug(f'- proxy {url}')


def addroute(basepath, endpoint):
    url = os.path.join(KOOPLEX['proxy'].get('url_api', 'http://localhost:8001/api'), 'routes', basepath) 
    headers = {'Authorization': 'token %s' % KOOPLEX['proxy'].get('auth_token', '') }
    data = json.dumps({ 'target': endpoint })
    requests.post(url, headers=headers, data=data)
    logging.debug(f'+ proxy {url} ({data})')


def removeroute(basepath):
    url = os.path.join(KOOPLEX['proxy'].get('url_api', 'http://localhost:8001/api'), 'routes', basepath)
    headers = {'Authorization': 'token %s' % KOOPLEX['proxy'].get('auth_token', '') }
    requests.delete(url, headers=headers)
    logging.debug(f'- proxy {url}')
