import django
from django.test import TestCase

from kooplex.lib.gitlab import Gitlab

class Test_gitlab(TestCase):

    TEST_USER = 'test'
    TEST_PASSWORD = 'almafa137'

    def make_gitlab_client(self):
        g = Gitlab()
        g.authenticate_user(Test_gitlab.TEST_USER, Test_gitlab.TEST_PASSWORD)
        return g

    def test_authenticate(self):
        g = Gitlab()
        res, user = g.authenticate_user(Test_gitlab.TEST_USER, Test_gitlab.TEST_PASSWORD)
        self.assertTrue(res)

    def test_get_projects(self):
        g = self.make_gitlab_client()
        pp = g.get_projects()


if __name__ == '__main__':
    unittest.main()
