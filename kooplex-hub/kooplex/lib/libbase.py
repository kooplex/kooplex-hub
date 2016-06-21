import json
import requests
from django.conf import settings
from threadlocals.threadlocals import get_current_request

def get_settings(block, value, defaults):
    s = getattr(settings, block)
    if s and value in s:
        return s[value]
    if type(defaults) is tuple:
        for d in defaults:
            if d:
                return d
    else:
        return defaults

class LibBase:

    def __init__(self, request=None):
        self.request = request
        return None
    
    def get_session_store(self):
        if self.request is not None:
            return self.request.session
        else:
            request = get_current_request()
            return request.session

    def http_prepare_url(self, url):
        return url

    def http_get(self, url, params=None, headers=None):
        res = requests.get(self.http_prepare_url(url),
                           params= params,
                           headers= headers)
        return res

    def http_post(self, url, params=None, headers=None, data=None):
        res = requests.post(self.http_prepare_url(url),
                            params= params,
                            headers= headers,
                            data=data)
        return res

    def http_delete(self, url, params=None, headers=None):
        res = requests.delete(self.http_prepare_url(url),
                             params=params,
                             headers=headers)
        return res