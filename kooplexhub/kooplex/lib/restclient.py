import json
import requests
import time
import logging

from kooplex.lib.libbase import LibBase
from kooplex.lib.debug import *

DEBUG_LOCAL=False

class RestClientError(Exception):
    pass

class RestClient(LibBase):

    def __init__(self, host='localhost', port=None, https=False, base_url=None):
        print_debug("",DEBUG_LOCAL)
        self.https = https
        self.host = host
        if not port:
            self.port = https if 443 else 80
        else:
            self.port = port
        self.base_url = base_url

    def http_prepare_url(self, path):
        print_debug("",DEBUG_LOCAL)
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
        print_debug("",DEBUG_LOCAL)
        url = self.http_prepare_url(url)
        params = self.http_prepare_parameters(params)
        headers = self.http_prepare_headers(headers)
        return url, params, headers

    def http_prepare_data(self, data):
        print_debug('',DEBUG_LOCAL)
        if not data:
            return None
        elif type(data) is dict:
            return json.dumps(data)
        else:
            return data
            
    def http_prepare_formdata(self, formdata):
        print_debug('',DEBUG_LOCAL)
        if not formdata:
            return None
        elif type(formdata) is dict:
            return json.dumps(formdata)
        else:
            return formdata

    def http_action(self, path, params, headers, data, expect, action, formdata=None):
        print_debug("",DEBUG_LOCAL)
        url, params, headers = self.http_prepare_request(path, params, headers)
        data = self.http_prepare_data(data)
#        formdata = self.http_prepare_formdata(formdata)
        if expect and type(expect) is not list:
            expect = [ expect ]
        s = 0.1
        while s < 10:
            if formdata:
                res = action(url=url, params=params, headers=headers, data=data, files=formdata)
            else:
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
        print_debug("",DEBUG_LOCAL)
        return self.http_action(path, params, headers, None, expect, requests.get)

    def http_post(self, path, params=None, headers=None, data=None, expect=None, formdata=None):
        print_debug("",DEBUG_LOCAL)
        return self.http_action(path, params, headers, data, expect, requests.post, formdata)

    def http_put(self, path, params=None, headers=None, data=None, expect=None):
        print_debug("",DEBUG_LOCAL)
        return self.http_action(path, params, headers, data, expect, requests.put)

    def http_patch(self, path, params=None, headers=None, data=None, expect=None):
        print_debug("",DEBUG_LOCAL)
        return self.http_action(path, params, headers, data, expect, requests.patch)

    def http_delete(self, path, params=None, headers=None, expect=None):
        print_debug("",DEBUG_LOCAL)
        return self.http_action(path, params, headers, None, expect, requests.delete)