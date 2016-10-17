import json
import requests
import time

from kooplex.lib.libbase import LibBase

class RestClientError(Exception):
    pass

class RestClient(LibBase):

    def __init__(self, host='localhost', port=None, https=False, base_url=None):
        self.https = https
        self.host = host
        if not port:
            self.port = https if 443 else 80
        else:
            self.port = port
        self.base_url = base_url

    def http_prepare_url(self, path):
        if self.base_url:
            url = LibBase.join_path(self.base_url, path)
        else:
            url = RestClient.make_url(self.host, path, self.port, self.https)
        return url

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

    def http_prepare_data(self, data):
        if not data:
            return None
        elif type(data) is dict:
            return json.dumps(data)
        else:
            return data

    def http_action(self, path, params, headers, data, expect, action):
        url, params, headers = self.http_prepare_request(path, params, headers)
        data = self.http_prepare_data(data)
        if expect and type(expect) is not list:
            expect = [ expect ]
        s = 0.1
        while s < 100:
            res = action(url=url, params=params, headers=headers, data=data)
            if res.status_code == 503:
                s *= 2
                time.sleep(s)
            else:
                if expect and res.status_code not in expect:
                    raise RestClientError(res.reason)
                return res
        raise RestClientError(res.reason)

    def http_get(self, path, params=None, headers=None, expect=None):
        return self.http_action(path, params, headers, None, expect, requests.get)

    def http_post(self, path, params=None, headers=None, data=None, expect=None):
        return self.http_action(path, params, headers, data, expect, requests.post)

    def http_put(self, path, params=None, headers=None, data=None, expect=None):
        return self.http_action(path, params, headers, data, expect, requests.put)

    def http_patch(self, path, params=None, headers=None, data=None, expect=None):
        return self.http_action(path, params, headers, data, expect, requests.patch)

    def http_delete(self, path, params=None, headers=None, expect=None):
        return self.http_action(path, params, headers, None, expect, requests.delete)