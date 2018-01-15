import os
import json
import requests
import time

from kooplex.lib import get_settings


class JupyterError(Exception):
    pass

class Jupyter:
    """Jupyter notebook api client.
    based on: https://gist.github.com/blink1073/ecae5130dfe138ea2aff
    """
    token = "aiSiga1aiFai2AiZu1veeWein5gijei8yeLay2Iecae3ahkiekeisheegh2ahgee"

    @staticmethod
    def _keeptrying(method, times, **kw):
        lastexception = None
        dt = .1
        while times > 0:
            times -= 1
            try:
                return method(**kw)
            except Exception as e:
                lastexception = e
                time.sleep(dt)
                dt *= 2
        if lastexcetion is not None:
            raise lastexception

    def start_session(self, container):
        info = { 'containername': container.name }
        kw = {
            'url': os.path.join(get_settings('spawner', 'pattern_jupyterapi') % info, 'sessions'), 
            'headers': {'Authorization': 'token %s' % self.token, }, #FIXME: to be replaced by container.token
            'data': json.dumps({'notebook': {'path': container.url }, 'kernel': { 'name': 'python3' }}),
        }
        return self._keeptrying(requests.post, 50, **kw)
        #FIXME: check for state (another call /api/kernels
