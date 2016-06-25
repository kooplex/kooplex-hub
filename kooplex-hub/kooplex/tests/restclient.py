import unittest
from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient

class Test_restclient(unittest.TestCase):
   

    def test_http_prepare_url(self):
        r = RestClient()
        self.assertEquals('http://localhost', r.http_prepare_url(''))
        self.assertEquals('http://localhost/test', r.http_prepare_url('test'))
        self.assertEquals('http://localhost/test', r.http_prepare_url('/test'))

if __name__ == '__main__':
    unittest.main()
