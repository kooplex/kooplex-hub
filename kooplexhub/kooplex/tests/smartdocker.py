import unittest
from kooplex.lib import Docker
from kooplex.hub.models import Container

class Test_docker(unittest.TestCase):

    TEST_CONTAINER = 'test-busybox'
    TEST_IMAGE = 'busybox:latest'
    TEST_COMMAND = '/bin/busybox sleep 1000' # keep container running

    def make_test_container(self):
        container = Container(
            name=Test_docker.TEST_CONTAINER, 
            image=Test_docker.TEST_IMAGE,
            command=Test_docker.TEST_COMMAND,
        )
        return container

    def test_get_docker_url(self):
        d = Docker(socket=True)
        url = d.get_docker_url()
        self.assertEqual('unix:///var/run/docker.sock', url)

        d = Docker(host='test', port=5555)
        url = d.get_docker_url()
        self.assertEqual('tcp://test:5555', url)

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
        c = self.make_test_container()
        d.ensure_image_exists(c.name)
        d.ensure_container_removed(c.name)
        d.create_container(c)
        c = d.get_container(c)
        self.assertEqual('created', c.state)
        c = d.get_container(c.name)
        self.assertEqual('created', c.state)
        d.ensure_container_removed(c)
        
    def test_list_containers(self):
        pass

    def test_ensure_container_exists(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_removed(c)
        d.ensure_container_exists(c)
        d.ensure_container_exists(c)
        d.ensure_container_removed(c)

    def test_start_container(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_exists(c)
        d.start_container(c)
        c = d.get_container(c)
        self.assertEqual('running', c.state)
        d.kill_container(c)
        d.ensure_container_removed(c)

    def test_ensure_container_running(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_removed(c)
        d.ensure_container_running(c)
        c = d.get_container(c)
        self.assertEqual('running', c.state)
        d.stop_container(c)
        c = d.get_container(c)
        self.assertEqual('exited', c.state)
        d.ensure_container_running(c)
        c = d.get_container(c)
        self.assertEqual('running', c.state)
        d.ensure_container_removed(c)

    def test_stop_container(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_running(c)
        c = d.get_container(c)
        self.assertEqual('running', c.state)
        d.stop_container(c)
        c = d.get_container(c)
        self.assertEqual('exited', c.state)
        d.ensure_container_removed(c)

    def test_kill_container(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_running(c)
        c = d.get_container(c)
        self.assertEqual('running', c.state)
        d.kill_container(c)
        c = d.get_container(c)
        self.assertEqual('exited', c.state)
        d.ensure_container_removed(c)

    def test_ensure_container_stopped(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_running(c)
        c = d.get_container(c)
        self.assertEqual('running', c.state)
        d.ensure_container_stopped(c)
        c = d.get_container(c)
        self.assertEqual('exited', c.state)
        c = d.get_container(c)
        self.assertEqual('exited', c.state)
        d.ensure_container_removed(c)
        # TODO: kill on timeout

    def test_remove_container(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_removed(c)
        d.ensure_container_exists(c)
        d.remove_container(c)
        c = d.get_container(c)
        self.assertIsNone(c)

    def test_ensure_container_removed(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_removed(c)
        d.ensure_container_exists(c)
        d.ensure_container_removed(c)
        d.ensure_container_running(c)
        d.ensure_container_removed(c)
        d.ensure_container_removed(c)

    def test_exec_container(self):
        d = Docker()
        c = self.make_test_container()
        d.ensure_container_running(c)
        c = d.get_container(c)
        self.assertEqual('running', c.state)
        d.exec_container(c, 'ls')
        d.ensure_container_removed(c)


if __name__ == '__main__':
    unittest.main()
