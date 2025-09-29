"""
@author: David Visontai, Jozsef Steger
"""
import os
import json
import requests
import logging

from ..conf import CONTAINER_SETTINGS

logger = logging.getLogger(__name__)

def getroutes():
    url = os.path.join(CONTAINER_SETTINGS['proxy']['url'], 'routes')
    headers = {'Authorization': 'token %s' % CONTAINER_SETTINGS['proxy']['auth_token'] }
    return requests.get(url, headers=headres)


def droproutes():
    resp = getroutes()
    routes = json.loads(resp.content.decode())
    headers = {'Authorization': 'token %s' % CONTAINER_SETTINGS['proxy']['auth_token'] }
    for r, v in routes.items():
        url = os.path.join(CONTAINER_SETTINGS['proxy']['url'], 'routes', r[1:])
        requests.delete(url, headers=headers)
        logging.debug(f'- proxy {url}')


def addroute(basepath, endpoint):
    url = os.path.join(CONTAINER_SETTINGS['proxy']['url'], 'routes', basepath) 
    headers = {'Authorization': 'token %s' % CONTAINER_SETTINGS['proxy']['auth_token'] }
    data = json.dumps({ 'target': endpoint })
    requests.post(url, headers=headers, data=data)
    logging.debug(f'+ proxy {url} ({data})')


def removeroute(basepath):
    url = os.path.join(CONTAINER_SETTINGS['proxy']['url'], 'routes', basepath)
    headers = {'Authorization': 'token %s' % CONTAINER_SETTINGS['proxy']['auth_token'] }
    requests.delete(url, headers=headers)
    logging.debug(f'- proxy {url}')
