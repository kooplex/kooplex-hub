import json
import requests

from kooplex.lib.libbase import LibBase

class RestClient(LibBase):

    def __init__(self, host='localhost', port=None, https=False):
        self.https = https
        self.host = host
        if not port:
            self.port = https if 443 else 80
        else:
            self.port = port

    def http_prepare_url(self, path):
        return RestClient.make_url(self.host, path, self.port, self.https)

    def http_prepare_parameters(self, params):
        if not params:
            params = {}
        return params

    def http_prepare_headers(self, headers):
        if not headers:
            headers = {}
        return headers

    def http_prepare_request(self, url, params, headers):
        url = self.http_prepare_url(url)
        params = self.http_prepare_parameters(params)
        headers = self.http_prepare_headers(headers)
        return url, params, headers

    def http_get(self, path, params=None, headers=None):
        url, params, headers = self.http_prepare_request(path, params, headers)
        res = requests.get(url=url, params=params, headers=headers)
        return res

    def http_post(self, path, params=None, headers=None, data=None):
        url, params, headers = self.http_prepare_request(path, params, headers)
        res = requests.post(url=url, params=params, headers=headers, data=json.dumps(data))
        return res

    def http_delete(self, path, params=None, headers=None):
        url, params, headers = self.http_prepare_request(path, params, headers)
        res = requests.delete(self.http_prepare_url(url),
                             params=params,
                             headers=headers)
        return res