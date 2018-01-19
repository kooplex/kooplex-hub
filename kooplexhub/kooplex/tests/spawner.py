import django
import unittest
import requests
import time
from kooplex.lib.spawner import Spawner

if __name__ == '__main__':
    unittest.main()

class Test_spawner(unittest.TestCase):
    """
    Test prerequisites:    
    - docker daemon running and listening
    - existing docker network with subnet specified
    - configurable-http-proxy running with access to docker subnet
    """

    TEST_USERNAME = 'jeges2'
    TEST_IMAGE = 'jupyter/minimal-notebook:latest'
    TEST_CONTAINER_NAME = 'test-notebook-{$username}'
    
    def make_spawner(self):
        s = Spawner(username=Test_spawner.TEST_USERNAME,
                    image=Test_spawner.TEST_IMAGE,
                    container_name=Test_spawner.TEST_CONTAINER_NAME)
        return s

    def test_pick_random_ip(self):
        s = self.make_spawner()
        ip = s.pick_random_ip()

    def test_get_container_name(self):
        s = self.make_spawner()
        n = s.get_container_name()
        self.assertEqual('test-notebook-test', n)

    def test_make_notebook(self):
        s = self.make_spawner()
        nb = s.make_notebook()
        self.assertIsNotNone(nb.id)
        self.assertEqual(Test_spawner.TEST_USERNAME, nb.username)
        self.assertIsNotNone(nb.docker_host)
        self.assertIsNotNone(nb.name)
        self.assertIsNotNone(nb.ip)
        self.assertEqual(Test_spawner.TEST_IMAGE, nb.image)
        self.assertIsNotNone(nb.port)
        self.assertIsNotNone(nb.proxy_path)
        self.assertIsNotNone(nb.external_url)
    
    def test_start_stop(self):
        s = Spawner(Test_spawner.TEST_USERNAME)

        s.ensure_notebook_stopped()

        nb = s.ensure_notebook_running()
        url = nb.external_url
        time.sleep(2)   # wait for notebook and proxy to start
        res = requests.get(url)
        self.assertEqual(200, res.status_code)

        nb = s.ensure_notebook_running()
        url = nb.external_url
        time.sleep(2)   # wait for notebook and proxy to start
        res = requests.get(url)
        self.assertEqual(200, res.status_code)

        s.ensure_notebook_stopped()

        nb = s.ensure_notebook_running()
        url = nb.external_url
        time.sleep(2)   # wait for notebook and proxy to start
        res = requests.get(url)
        self.assertEqual(200, res.status_code)

        s.ensure_notebook_stopped()

    def start_kernel(self, notebook, kernel):
        raise NotImplementedError

    def stop_kernel(self, notebook, kernel):
        raise NotImplementedError

