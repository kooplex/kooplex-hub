"""
@author: David Visontai, Jozsef Steger
"""
import os
import json
import requests
import logging

from kooplex.settings import KOOPLEX

from kooplex.lib import keeptrying

logger = logging.getLogger(__name__)

def addroute(container):
    proxyconf = KOOPLEX.get('proxy', {})
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', container.proxy_path), 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
        'data': json.dumps({ 'target': container.url }),
    }
    logging.debug("+ %s ---> %s" % (kw['url'], container.url))
    return keeptrying(requests.post, 50, **kw)

def removeroute(container):
    proxyconf = KOOPLEX.get('proxy', {})
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', container.proxy_path), 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
    }
    logging.debug("- %s -/-> %s" % (kw['url'], container.url))
    return keeptrying(requests.delete, 5, **kw)
 
