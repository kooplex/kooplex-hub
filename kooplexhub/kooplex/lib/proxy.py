"""
@author: David Visontai, Jozsef Steger
"""
import os
import json
import requests
import logging

from kooplex.settings import KOOPLEX
#from hub.models import Container, Report
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
#    return resp_latest

def addroute(environment):
    proxyconf = KOOPLEX.get('proxy', {})
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', f'notebook/{environment.name}'), #FIXME 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
        'data': json.dumps({ 'target': f'http://{environment.name}:8000' }), #FIXME
    }
    logging.debug(f'+ proxy {kw["url"]} ---> http://{environment.name}:8000') #FIXME
    return keeptrying(requests.post, 50, **kw)

def removeroute(environment):
    proxyconf = KOOPLEX.get('proxy', {})
    kw = {
        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', f'notebook/{environment.name}'), #FIXME 
        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
    }
    logging.debug(f'- proxy {kw["url"]} -/-> http://{environment.name}:8000') #FIXME
    return keeptrying(requests.delete, 5, **kw)

#def _removeroute_report(report):
#    proxyconf = KOOPLEX.get('proxy', {})
#    reportconf = KOOPLEX.get('reportserver', {})
#    target_url = reportconf.get('base_url', 'localhost')
#    kw = {
#        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', report.proxy_path), 
#        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#    }
#    logging.debug("- %s -/-> %s" % (kw['url'], target_url))
#    return keeptrying(requests.delete, 5, **kw)
#
#def removeroute(instance):
#    if isinstance(instance, Container):
#        return _removeroute_container(instance)
#    elif isinstance(instance, Report):
#        return _removeroute_report(instance)
#    logger.error('Not implemented')

 
#def _addroute_report(report):
#    proxyconf = KOOPLEX.get('proxy', {})
#    reportconf = KOOPLEX.get('reportserver', {})
#    target_url = reportconf.get('base_url', 'localhost')
#    route_prefix = 'report'
#    if report.reporttype != report.TP_STATIC:
#        route_prefix = 'notebook'
#        target_url = report.url_external
#    kw = {
#        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', route_prefix, report.proxy_path), 
#        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#        'data': json.dumps({ 'target': target_url }),
#    }
#    logging.debug("+ %s ---> %s" % (kw['url'], target_url))
#    keeptrying(requests.post, 50, **kw)
#
#    kw = {
#        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', route_prefix, report.proxy_path_latest), 
#        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#        'data': json.dumps({ 'target': target_url }),
#    }
#    logging.debug("Report proxy + %s ---> %s" % (kw['url'], target_url))
#    return keeptrying(requests.post, 50, **kw)
#
#def addroute(instance):
#    if isinstance(instance, Container):
#        _addroute_container(instance, test=False)
#        return _addroute_container(instance, test=True)
#    elif isinstance(instance, Report):
#        return _addroute_report(instance)
#    logger.error('Not implemented %s type %s' % (instance, type(instance)))

#def _addroute_container(container, test=False):
#    proxyconf = KOOPLEX.get('proxy', {})
#    if test:
#        kw = {
#            'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', container.proxy_path_test), 
#            'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#            'data': json.dumps({ 'target': container.url_test }),
#        }
#        logging.debug("+ %s ---> %s test port" % (kw['url'], container.url_test))
#    else:
#        kw = {
#            'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', container.proxy_path), 
#            'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#            'data': json.dumps({ 'target': container.url }),
#        }
#        logging.debug("+ %s ---> %s proxy path" % (kw['url'], container.url))
#        try:
#             rc = ReportContainerBinding.objects.get(container = container)
#             report = rc.report
#             kw = {
#                 'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', 'notebook', report.proxy_path_latest), 
#                 'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#                 'data': json.dumps({ 'target': container.url_test }),
#             }
#             logging.debug("+ %s ---> %s report proxy path latest" % (kw['url'], container.url))
#             keeptrying(requests.post, 50, **kw)
#        except: 
#             logging.debug("Container is not for report")
#
#
#    logging.debug("+ %s ---> %s" % (kw['url'], container.url))
#    return keeptrying(requests.post, 50, **kw)
#
# 
#def _addroute_report(report):
#    proxyconf = KOOPLEX.get('proxy', {})
#    reportconf = KOOPLEX.get('reportserver', {})
#    target_url = reportconf.get('base_url', 'localhost')
#    route_prefix = 'report'
#    if report.reporttype != report.TP_STATIC:
#        route_prefix = 'notebook'
#        target_url = report.url_external
#    kw = {
#        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', route_prefix, report.proxy_path), 
#        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#        'data': json.dumps({ 'target': target_url }),
#    }
#    logging.debug("+ %s ---> %s" % (kw['url'], target_url))
#    keeptrying(requests.post, 50, **kw)
#
#    kw = {
#        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', route_prefix, report.proxy_path_latest), 
#        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#        'data': json.dumps({ 'target': target_url }),
#    }
#    logging.debug("Report proxy + %s ---> %s" % (kw['url'], target_url))
#    return keeptrying(requests.post, 50, **kw)
#
#def addroute(instance):
#    if isinstance(instance, Container):
#        _addroute_container(instance, test=False)
#        return _addroute_container(instance, test=True)
#    elif isinstance(instance, Report):
#        return _addroute_report(instance)
#    logger.error('Not implemented %s type %s' % (instance, type(instance)))


#def _removeroute_container(container):
#    proxyconf = KOOPLEX.get('proxy', {})
#    kw = {
#        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', container.proxy_path), 
#        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#    }
#    logging.debug("- %s -/-> %s" % (kw['url'], container.url))
#    return keeptrying(requests.delete, 5, **kw)
#
#def _removeroute_report(report):
#    proxyconf = KOOPLEX.get('proxy', {})
#    reportconf = KOOPLEX.get('reportserver', {})
#    target_url = reportconf.get('base_url', 'localhost')
#    kw = {
#        'url': os.path.join(proxyconf.get('base_url','localhost'), 'api', 'routes', report.proxy_path), 
#        'headers': {'Authorization': 'token %s' % proxyconf.get('auth_token', '') },
#    }
#    logging.debug("- %s -/-> %s" % (kw['url'], target_url))
#    return keeptrying(requests.delete, 5, **kw)
#
#def removeroute(instance):
#    if isinstance(instance, Container):
#        return _removeroute_container(instance)
#    elif isinstance(instance, Report):
#        return _removeroute_report(instance)
#    logger.error('Not implemented')

