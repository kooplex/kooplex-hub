import unittest
from kooplex.lib.proxy import Proxy, ProxyError

class Test_proxy(unittest.TestCase):
    
    def make_proxy(self):
        p = Proxy(host='proxy', port=8001, auth_token='testtoken', https=False, external_url='http://external/path')
        return p

    def test_http_prepare_headers(self):
        p = self.make_proxy()
        self.assertEqual({'Authorization': 'token testtoken'}, p.http_prepare_headers(None))

    def test_get_external_url(self):
        p = self.make_proxy()
        self.assertEqual('http://external/path/morepath', p.get_external_url('morepath'))

    def test_make_route(self):
        p = self.make_proxy()
        self.assertEqual(
            ('/api/routes/test',
             {'target':'http://host:8888'}),
            p.make_route('test', 'host', 8888))

    def test_add_route(self):
        p = Proxy()
        p.add_route('test', 'host', 8888)

    def test_get_route(self):
        p = Proxy()
        p.add_route('test', 'host', 8888)
        self.assertEqual('http://host:8888', p.get_route('test')['/test']['target'])
        # NOTE: proxy returns something, even if route doesn't exist
        p.get_route('nonexistantroute')
            

if __name__ == '__main__':
    unittest.main()
