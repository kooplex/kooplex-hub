import unittest
from kooplex.lib.repo import Repo

class Test_repo(unittest.TestCase):

    TEST_USERNAME = 'test'
    TEST_REPO_NAME = 'test/alma'

    def make_repo(self):
        r = Repo(Test_repo.TEST_USERNAME, Test_repo.TEST_REPO_NAME)
        return r

    def test_init_local(self):
        r = self.make_repo()

        r.ensure_local_dir_empty()
        r.init_local()
        self.assertTrue(r.is_local_existing())
        
        r.delete_local()

    def test_get_local(self):
        r = self.make_repo()

        r.ensure_local_dir_empty()
        r.init_local()

        rr = r.get_local()
        self.assertFalse(rr.bare)

    def test_clone_http(self):
        r = self.make_repo()
        r.proto = 'http'

        r.ensure_local_dir_empty()
        rr = r.clone()
        self.assertFalse(rr.bare)

    def test_clone_http(self):
        r = self.make_repo()
        r.proto = 'http'

        r.ensure_local_dir_empty()
        rr = r.clone()
        self.assertFalse(rr.bare)

    def test_clone_ssh(self):
        r = self.make_repo()
        r.proto = 'ssh'

        r.ensure_local_dir_empty()
        rr = r.clone()
        self.assertFalse(rr.bare)

if __name__ == '__main__':
    unittest.main()
