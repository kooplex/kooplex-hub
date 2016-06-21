import django
import unittest
import requests
import time
from kooplex.lib.spawner import Spawner


class Test_spawner(unittest.TestCase):
    """
    Test prerequisites:    
    - docker daemon running and listening
    - existing docker network with subnet specified
    - configurable-http-proxy running with access to docker subnet
    """

    if django.VERSION[:2] >= (1, 7):
        # Django 1.7 requires an explicit setup() when running tests in PTVS
        @classmethod
        def setUpClass(cls):
            django.setup()
    
    def create_spawner(self):
        s = Spawner('test', 'jupyter/minimal-notebook:latest')
        return s

    def test_spawner_init(self):
        self.create_spawner()

    ### -------------------------------------------------------
    ### Utility functions

    def test_spawner_get_random_ip(self):
        s = self.create_spawner()
        ip = s.get_random_ip()

    def test_spawner_get_random_port(self):
        s = self.create_spawner()
        port = s.get_random_port()

    ### -------------------------------------------------------
    ### Docker setup

    def test_spawner_get_network(self):
        s = self.create_spawner()
        net = s.get_network()

    def test_spawner_pull_image(self):
        s = self.create_spawner()
        img = s.pull_image()
        self.assertEqual(img['Id'], 'sha256:fd00230f33b54163ac4637f39bf57039beb19c75972af868762589507d705e5e')

    def test_spawner_ensure_image_exists(self):
        s = self.create_spawner()
        img = s.ensure_image_exists()
        self.assertEqual(img['Id'], 'sha256:fd00230f33b54163ac4637f39bf57039beb19c75972af868762589507d705e5e')

    def test_spawner_create_get_remove_container(self):
        s = self.create_spawner()
        s.ensure_container_removed('test')

        c = s.create_container('test')
        self.assertEqual(c['State'], 'created')
        s.remove_container('test')
        c = s.get_container('test')
        self.assertIsNone(c)

        s.ensure_container_removed('test')

    def test_spawner_ensure_container_exists(self):
        s = self.create_spawner()
        s.ensure_container_removed('test')

        c = s.ensure_container_exists('test')
        self.assertEqual(c['State'], 'created')
        s.remove_container('test')
        c = s.get_container('test')
        self.assertIsNone(c)

        s.ensure_container_removed('test')

    def test_spawner_list_containers(self):
        raise NotImplementedError

    def test_spawner_start_container(self):
        s = self.create_spawner()
        s.ensure_container_removed('test')

        c = s.start_container('test')
        self.assertEqual(c['State'], 'running')

        s.ensure_container_removed('test')

    def test_spawner_ensure_container_running(self):
        s = self.create_spawner()
        s.ensure_container_removed('test')
        
        c = s.ensure_container_running('test')
        self.assertEqual(c['State'], 'running')
        
        s.ensure_container_removed('test')

    ### -------------------------------------------------------
    ### Proxy setup

    def test_spawner_create_route(self):
        s = self.create_spawner()

        url, data = s.create_route('test', 'host', 16888,)
        self.assertGreaterEqual(url.find('/api/routes/test'), 0)
        self.assertGreaterEqual(data.find(':16888'), 0)

    def test_spawner_add_get_remove_route(self):
        s = self.create_spawner()

        s.add_route('test', 'host', 8081)
        s.get_route('test')
        s.remove_route('test')

    ### -------------------------------------------------------
    ### Kernel spawner

    def test_spawner_get_kernel_container(self):
        s = self.create_spawner()
        name = s.get_kernel_container()
        self.assertEqual(name, 'kooplex-jupyter-test')

    def test_spawner_spawn_kernel(self):
        s = self.create_spawner()
        k = s.spawn_kernel()
        url = k.url
        time.sleep(2)   # wait for kernel and proxy to start
        res = requests.get(url)
        self.assertEqual(200, res.status_code)




if __name__ == '__main__':
    unittest.main()
