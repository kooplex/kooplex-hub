"""
@author: David Visontai, Jozsef Steger
"""
import os
import json
import requests
import logging

from kooplex.settings import KOOPLEX
from kooplex.lib import keeptrying, standardize_str

logger = logging.getLogger(__name__)

reportconf = KOOPLEX.get('reportserver', {})

def removeroute(instance):
    if isinstance(instance, Container):
        return _removeroute_container(instance)
    elif isinstance(instance, Report):
        return _removeroute_report(instance)
    logger.error('Not implemented')

def add_report_nginx_api(report):
#    import htpasswd
    str_name = standardize_str(report.proxy_path)
    conf_text="""
location /report/%s {
auth_basic "Administrator Login";
auth_basic_user_file /etc/passwords/%s;

}
    """%(report.proxy_path, standardize_str(report.proxy_path))
    logging.debug("+ pw registration ---> %s" % (str_name))
    kw = {
          'url': os.path.join(reportconf.get('api_url','localhost'), 'api', 'new', str_name),
          'data': json.dumps({ 
              'conf': conf_text,
              'username' : 'report',
              'password' : report.password
              }),
          'auth': ("nginxuser", 'nginxpw'),

    }
    logging.debug("+ %s ---> %s" % (kw['url'], kw['data']))
    keeptrying(requests.post, 50, **kw)

def remove_report_nginx_api(report):
    str_name = standardize_str(report.proxy_path)
    kw = {
          'url': os.path.join(reportconf.get('api_url','localhost'), 'api', 'remove', str_name),
          'data': json.dumps({ 
              }),
          'auth': ("nginxuser", 'nginxpw'),

    }
    logging.debug("- %s ---> %s" % (kw['url'], kw['data']))
    return keeptrying(requests.delete, 5, **kw)
