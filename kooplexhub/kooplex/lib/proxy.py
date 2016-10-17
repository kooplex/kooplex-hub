from kooplex.lib.libbase import LibBase
from kooplex.lib.libbase import get_settings
from kooplex.lib.restclient import RestClient

class ProxyError(Exception):
    pass

class Proxy(RestClient):

    def __init__(self, host=None, port=None, auth_token=None, https=None, external_url=None):
        host = get_settings('proxy', 'host', host, '127.0.0.1')
        port = get_settings('proxy', 'port', port, 8001)
        https = get_settings('proxy', 'https', https, False)
        RestClient.__init__(self, host, port, https)
        
        self.auth_token = get_settings('proxy', 'auth_token', auth_token, None)
        self.external_url = get_settings('proxy', 'external_url', external_url, 'http://localhost')

    def http_prepare_headers(self, headers):
        headers = RestClient.http_prepare_headers(self, headers)
        if self.auth_token:
            headers['Authorization'] = 'token ' + self.auth_token
        return headers

    def get_external_url(self, path):
        url = RestClient.join_path(self.external_url, path)
        return url

    def make_path(self, path):
        path = RestClient.join_path('/api/routes/', path)
        return path

    def make_route(self, path, host=None, port=None, https=None):
        path = self.make_path(path)
        target = RestClient.make_url(host=host, port=port, https=https)
        data = {'target': target}
        return path, data

    def add_route(self, path, host, port, https=False):
        path, data = self.make_route(path, host, port, https)
        res = self.http_post(path, data=data)
        if res.status_code != 201:
            raise ProxyError

    def get_route(self, path):
        path = self.make_path(path)
        res = self.http_get(path)
        # NOTE: proxy returns something, even if route doesn't exist
        #if res.status_code != 200:
        #    raise ProxyError
        return res.json()

    def remove_route(self, path):
        #url, data = self.make_route(path)
        res = self.get_route(path)
        url = res[path]['target']
        res = self.http_delete(url)
