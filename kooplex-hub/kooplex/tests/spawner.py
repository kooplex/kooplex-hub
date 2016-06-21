import unittest
from kooplex.lib.spawner import Spawner

class Test_spawner(unittest.TestCase):
    
    def create_spawner(self):
        s = Spawner('test', 'debian:jessie', 'ubuntu-pollux', 5555)
        return s

    def test_spawner_init(self):
        self.create_spawner()

    ### -------------------------------------------------------
    ### Proxy setup

    def test_spawner_create_route(self):
        s = self.create_spawner()
        url, data = s.create_route('test', 'host', 16888, )
        self.assertGreaterEqual(0, url.find('/api/routes/hub/test'))
        self.assertGreaterEqual(0, data.find('http://host:16888/test'))

    def test_spawner_add_remove_route(self):
        s = self.create_spawner()
        s.add_route('test', 'host', 8081)
        s.get_route('test')
        s.remove_route('test')

    ### -------------------------------------------------------
    ### Kernel spawner

    def test_spawner_get_random_port(self):
        s = self.create_spawner()
        s.get_random_port()
        return None

if __name__ == '__main__':
    unittest.main()
