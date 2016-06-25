import json
import requests

class RestClient():

    def __init__(self, host='localhost', port=None, https=False):
        self.https = https
        self.host = host
        if not port:
            self.port = https if 443 else 80
        else:
            self.port = port

    def join_url(a, b):
        if not b or len(b) == 0:
            url = a
        elif a[-1] != '/' and b[0] != '/':
            url = a + '/' + b
        elif a[-1] == '/' and b[0] == '/':
            url = a + b[1:]
        else:
            url = a + b
        return url

    def make_url(host='localhost', path=None, port=None, https=False):
        proto = 'https://' if https else 'http://'
        port = '' if (not port or not https and port == 80 or https and port == 443) else ':' + str(port)
        url = RestClient.join_url(proto + host + port, path)
        return url

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