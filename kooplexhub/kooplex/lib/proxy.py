"""
@author: David Visontai, Jozsef Steger
"""
import os
import json
import requests
import logging

from kooplex.settings import KOOPLEX
from hub.models import Container, Report
from kooplex.lib import keeptrying

logger = logging.getLogger(__name__)

def getroutes():
    proxyconf = KOOPLEX.get('proxy', {})
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes'), 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
    }
    return keeptrying(requests.get, 50, **kw)


def droproutes():
    proxyconf = KOOPLEX.get('proxy', {})
    resp = getroutes()
    routes = json.loads(resp.content.decode())
    for r, v in routes.items():
        kw = {
            'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', r[1:]), 
            'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
        }
        logging.debug("- %s -/-> %s" % (kw['url'], v['target']))
        resp_latest = keeptrying(requests.delete, 5, **kw)
    return resp_latest


def _addroute_container(container):
    proxyconf = KOOPLEX.get('proxy', {})
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', container.proxy_path), 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
        'data': json.dumps({ 'target': container.url }),
    }
    logging.debug("+ %s ---> %s" % (kw['url'], container.url))
    return keeptrying(requests.post, 50, **kw)

 
def _addroute_report(report):
    proxyconf = KOOPLEX.get('proxy', {})
    target_url = os.path.join('http://kooplex-test-report-nginx') # FIXME: settings.py
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', 'report', report.proxy_path), 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
        'data': json.dumps({ 'target': target_url }),
    }
    logging.debug("+ %s ---> %s" % (kw['url'], target_url))
    keeptrying(requests.post, 50, **kw)

    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', 'report', report.proxy_path_latest), 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
        'data': json.dumps({ 'target': target_url }),
    }
    logging.debug("+ %s ---> %s" % (kw['url'], target_url))
    return keeptrying(requests.post, 50, **kw)

def addroute(instance):
    if isinstance(instance, Container):
        return _addroute_container(instance)
    elif isinstance(instance, Report):
        return _addroute_report(instance)
    logger.error('Not implemented %s type %s' % (instance, type(instance)))


def _removeroute_container(container):
    proxyconf = KOOPLEX.get('proxy', {})
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', container.proxy_path), 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
    }
    logging.debug("- %s -/-> %s" % (kw['url'], container.url))
    return keeptrying(requests.delete, 5, **kw)

def _removeroute_report(report):
    proxyconf = KOOPLEX.get('proxy', {})
    target_url = os.path.join('http://kooplex-test-report-nginx') # FIXME: settings.py
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', report.proxy_path), 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
    }
    logging.debug("- %s -/-> %s" % (kw['url'], target_url))
    return keeptrying(requests.delete, 5, **kw)

def removeroute(instance):
    if isinstance(instance, Container):
        return _removeroute_container(instance)
    elif isinstance(instance, Report):
        return _removeroute_report(instance)
    logger.error('Not implemented')

