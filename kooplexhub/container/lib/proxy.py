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

def addroute(container, var_url, var_port):
    proxyconf = KOOPLEX.get('proxy', {})
    port = KOOPLEX['environmental_variables'][var_port]
    namespace = KOOPLEX['kubernetes']['namespace']
    url = os.path.join(KOOPLEX['proxy'].get('url_api', 'http://localhost:8001/api'), 'routes', KOOPLEX['environmental_variables'][var_url].format(container=container)) 
    headers = {'Authorization': 'token %s' % KOOPLEX['proxy'].get('auth_token', '') }
    data = json.dumps({ 'target': 'http://{container.label}.{kubernetes_namespace}:{port}'.format(container=container, kubernetes_namespace=namespace, port=port )})
    requests.post(url, headers=headers, data=data)
    logging.debug(f'+ proxy {url} ({data})')

def removeroute(container, var_url):
    proxyconf = KOOPLEX.get('proxy', {})
    url = os.path.join(KOOPLEX['proxy'].get('url_api', 'http://localhost:8001/api'), 'routes', KOOPLEX['environmental_variables'][var_url].format(container=container))
    headers = {'Authorization': 'token %s' % KOOPLEX['proxy'].get('auth_token', '') }
    requests.delete(url, headers=headers)
    logging.debug(f'- proxy {url}')


