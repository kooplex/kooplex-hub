import os
import json
import requests
import time

from kooplex.lib import get_settings


def _keeptrying(method, times, **kw):
    dt = .1
    while times > 0:
        times -= 1
        try:
            return method(**kw)
        except Exception as e:
            if times == 0:
                raise
            time.sleep(dt)
            dt *= 2

#FIXME: these classes arent required, use methods instead
class Jupyter:
    """Jupyter notebook api client.
    based on: https://gist.github.com/blink1073/ecae5130dfe138ea2aff
    """
    token = "aiSiga1aiFai2AiZu1veeWein5gijei8yeLay2Iecae3ahkiekeisheegh2ahgee"


    def start_session(self, container):
        info = { 'containername': container.name }
        kw = {
            'url': os.path.join(get_settings('spawner', 'pattern_jupyterapi') % info, 'sessions'), 
            'headers': {'Authorization': 'token %s' % self.token, }, #FIXME: to be replaced by container.token
            'data': json.dumps({'notebook': {'path': container.url }, 'kernel': { 'name': 'python3' }}),
        }
        return _keeptrying(requests.post, 50, **kw)
        #FIXME: check for state (another call /api/kernels

class Proxy:
    def add_route(self, container):
        kw = {
            'url': os.path.join(get_settings('proxy', 'base_url'), 'api', 'routes', container.proxy_path), 
            'headers': {'Authorization': 'token %s' % get_settings('proxy', 'auth_token') },
            'data': json.dumps({ 'target': container.url }),
        }
        return _keeptrying(requests.post, 50, **kw)

    def remove_route(self, container):
        kw = {
            'url': os.path.join(get_settings('proxy', 'base_url'), 'api', 'routes', container.proxy_path), 
            'headers': {'Authorization': 'token %s' % get_settings('proxy', 'auth_token') },
        }
        return _keeptrying(requests.delete, 5, **kw)
 
