import unittest
from kooplex.lib.restclient import RestClient

class Test_restclient(unittest.TestCase):
    
    def test_join_url(self):
        self.assertEqual('http://localhost', RestClient.join_url('http://localhost', None))
        self.assertEqual('http://localhost', RestClient.join_url('http://localhost', ''))
        self.assertEqual('http://localhost/', RestClient.join_url('http://localhost/', ''))
        self.assertEqual('http://localhost/', RestClient.join_url('http://localhost/', '/'))
        self.assertEqual('http://localhost/', RestClient.join_url('http://localhost', '/'))
        self.assertEqual('http://localhost/test', RestClient.join_url('http://localhost', 'test'))
        self.assertEqual('http://localhost/test', RestClient.join_url('http://localhost/', 'test'))
        self.assertEqual('http://localhost/test', RestClient.join_url('http://localhost/', 'test'))
        self.assertEqual('http://localhost/test', RestClient.join_url('http://localhost/', '/test'))

    def test_make_url(self):
        self.assertEqual('http://localhost', RestClient.make_url())
        self.assertEqual('http://test', RestClient.make_url('test'))
        self.assertEqual('http://test/test', RestClient.make_url('test', 'test', 80))
        self.assertEqual('http://test:81/test', RestClient.make_url('test', 'test', 81))
        self.assertEqual('https://test/test', RestClient.make_url('test', 'test', None, True))
        self.assertEqual('https://test:80/test', RestClient.make_url('test', 'test', 80, True))
        self.assertEqual('https://test/test', RestClient.make_url('test', 'test', 443, True))

    def test_http_prepare_url(self):
        r = RestClient()
        self.assertEquals('http://localhost', r.http_prepare_url(''))
        self.assertEquals('http://localhost/test', r.http_prepare_url('test'))
        self.assertEquals('http://localhost/test', r.http_prepare_url('/test'))

if __name__ == '__main__':
    unittest.main()
