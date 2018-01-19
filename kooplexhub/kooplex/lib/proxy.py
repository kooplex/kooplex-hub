"""
@author: David Visontai, Jozsef Steger
"""
import os
import json
import requests
import logging

from kooplex.lib import get_settings, keeptrying

logger = logging.getLogger(__name__)

def addroute(container):
    kw = {
        'url': os.path.join(get_settings('proxy', 'base_url'), 'api', 'routes', container.proxy_path), 
        'headers': {'Authorization': 'token %s' % get_settings('proxy', 'auth_token') },
        'data': json.dumps({ 'target': container.url }),
    }
    logging.debug("+ %s ---> %s" % (kw['url'], container.url))
    return keeptrying(requests.post, 50, **kw)

def removeroute(container):
    kw = {
        'url': os.path.join(get_settings('proxy', 'base_url'), 'api', 'routes', container.proxy_path), 
        'headers': {'Authorization': 'token %s' % get_settings('proxy', 'auth_token') },
    }
    logging.debug("- %s -/-> %s" % (kw['url'], container.url))
    return keeptrying(requests.delete, 5, **kw)
 
