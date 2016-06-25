import unittest
from kooplex.lib import Docker

class Test_docker(unittest.TestCase):

    TEST_CONTAINER = 'test-busybox'
    TEST_IMAGE = 'busybox:latest'
    TEST_COMMAND = '/bin/busybox sleep 1000' # keep container running

    def test_make_docker_client(self):
        d = Docker(socket=True)
        cli = d.make_docker_client()
        self.assertEqual('http+docker://localunixsocket', cli.base_url)

        d = Docker(host="test", port=5555, network=None)
        cli = d.make_docker_client()
        self.assertEqual('http://test:5555', cli.base_url)

    def test_get_network(self):
        d = Docker()
        net = d.get_network()
        self.assertEqual('bridge', net['Driver'])

    def test_get_image(self):
        d = Docker()
        img = d.pull_image(Test_docker.TEST_IMAGE)
        img = d.get_image(Test_docker.TEST_IMAGE)
        self.assertEqual([Test_docker.TEST_IMAGE], img['RepoTags'])

    def test_pull_image(self):
        d = Docker()
        img = d.pull_image(Test_docker.TEST_IMAGE)
        self.assertEqual([Test_docker.TEST_IMAGE], img['RepoTags'])
        d.remove_image(Test_docker.TEST_IMAGE)

    def test_build_image(self):
        pass

    def test_ensure_image_exists(self):
        d = Docker()
        img = d.pull_image(Test_docker.TEST_IMAGE)
        d.ensure_image_exists(Test_docker.TEST_IMAGE)
        d.remove_image(Test_docker.TEST_IMAGE)
        d.ensure_image_exists(Test_docker.TEST_IMAGE)
        d.remove_image(Test_docker.TEST_IMAGE)

    def test_remove_image(self):
        d = Docker()
        d.ensure_image_exists(Test_docker.TEST_IMAGE)
        d.remove_image(Test_docker.TEST_IMAGE)
        self.assertIsNone(d.get_image(Test_docker.TEST_IMAGE))

    def test_create_get_container(self):
        d = Docker()
        d.ensure_image_exists(Test_docker.TEST_IMAGE)
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)
        d.create_container(Test_docker.TEST_CONTAINER, Test_docker.TEST_IMAGE)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('created', c['State'])
    
    def test_get_container_ip(self):
        d = Docker()
        d.ensure_image_exists(Test_docker.TEST_IMAGE)
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)
        d.create_container(Test_docker.TEST_CONTAINER, Test_docker.TEST_IMAGE, ip='172.18.0.1')
        ip = d.get_container_ip(Test_docker.TEST_CONTAINER)
        self.assertEqual('172.18.0.1', ip)
        
    def test_list_containers(self):
        pass

    def test_ensure_container_exists(self):
        d = Docker()
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)
        d.ensure_container_exists(Test_docker.TEST_CONTAINER, Test_docker.TEST_IMAGE)
        d.ensure_container_exists(Test_docker.TEST_CONTAINER, Test_docker.TEST_IMAGE)

    def test_start_container(self):
        d = Docker()
        d.ensure_container_exists(
            Test_docker.TEST_CONTAINER, 
            Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND)
        d.start_container(Test_docker.TEST_CONTAINER)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('running', c['State'])
        d.kill_container(Test_docker.TEST_CONTAINER)

    def test_ensure_container_running(self):
        d = Docker()
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)
        d.ensure_container_running(Test_docker.TEST_CONTAINER, 
            Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('running', c['State'])
        d.stop_container(Test_docker.TEST_CONTAINER)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('exited', c['State'])
        d.ensure_container_running(Test_docker.TEST_CONTAINER)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('running', c['State'])

    def test_stop_container(self):
        d = Docker()
        d.ensure_container_running(Test_docker.TEST_CONTAINER, 
            Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('running', c['State'])
        d.stop_container(Test_docker.TEST_CONTAINER)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('exited', c['State'])

    def test_kill_container(self):
        d = Docker()
        d.ensure_container_running(Test_docker.TEST_CONTAINER, 
            Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('running', c['State'])
        d.kill_container(Test_docker.TEST_CONTAINER)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('exited', c['State'])

    def test_ensure_container_stopped(self):
        d = Docker()
        d.ensure_container_running(Test_docker.TEST_CONTAINER, 
            Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('running', c['State'])
        d.ensure_container_stopped(Test_docker.TEST_CONTAINER)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('exited', c['State'])
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('exited', c['State'])
        # TODO: kill on timeout

    def test_remove_container(self):
        d = Docker()
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)
        d.ensure_container_exists(Test_docker.TEST_CONTAINER, Test_docker.TEST_IMAGE)
        d.remove_container(Test_docker.TEST_CONTAINER)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertIsNone(c)

    def test_ensure_container_removed(self):
        d = Docker()
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)
        d.ensure_container_exists(
            Test_docker.TEST_CONTAINER, 
            Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND)
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)
        d.ensure_container_running(
            Test_docker.TEST_CONTAINER, 
            Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND)
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)
        d.ensure_container_removed(Test_docker.TEST_CONTAINER)

    def test_exec_container(self):
        d = Docker()
        d.ensure_container_running(
            Test_docker.TEST_CONTAINER, 
            Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND)
        c = d.get_container(Test_docker.TEST_CONTAINER)
        self.assertEqual('running', c['State'])
        d.exec_container(Test_docker.TEST_CONTAINER, 'ls')


if __name__ == '__main__':
    unittest.main()
