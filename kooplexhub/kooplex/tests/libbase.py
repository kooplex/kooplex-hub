import unittest

from kooplex.lib.libbase import LibBase

class Test_libbase(unittest.TestCase):

    def test_join_path(self):
        self.assertEqual('http://localhost', LibBase.join_path('http://localhost', None))
        self.assertEqual('http://localhost', LibBase.join_path('http://localhost', ''))
        self.assertEqual('http://localhost/', LibBase.join_path('http://localhost/', ''))
        self.assertEqual('http://localhost/', LibBase.join_path('http://localhost/', '/'))
        self.assertEqual('http://localhost/', LibBase.join_path('http://localhost', '/'))
        self.assertEqual('http://localhost/test', LibBase.join_path('http://localhost', 'test'))
        self.assertEqual('http://localhost/test', LibBase.join_path('http://localhost/', 'test'))
        self.assertEqual('http://localhost/test', LibBase.join_path('http://localhost/', 'test'))
        self.assertEqual('http://localhost/test', LibBase.join_path('http://localhost/', '/test'))

    def test_make_url(self):
        self.assertEqual('http://localhost', LibBase.make_url())
        self.assertEqual('http://test', LibBase.make_url('test'))
        self.assertEqual('http://test/test', LibBase.make_url('test', 'test', 80))
        self.assertEqual('http://test:81/test', LibBase.make_url('test', 'test', 81))
        self.assertEqual('https://test/test', LibBase.make_url('test', 'test', None, True))
        self.assertEqual('https://test:80/test', LibBase.make_url('test', 'test', 80, True))
        self.assertEqual('https://test/test', LibBase.make_url('test', 'test', 443, True))

if __name__ == '__main__':
    unittest.main()
