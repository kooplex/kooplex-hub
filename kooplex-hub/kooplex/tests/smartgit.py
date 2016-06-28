import unittest
from kooplex.lib.smartgit import Git

class Test_git(unittest.TestCase):

    TEST_USERNAME = 'test'
    TEST_REPO_NAME = 'test/alma'

    def test_clone_repo(self):
        g = Git(Test_git.TEST_USERNAME)
        r = g.get_repo(Test_git.TEST_REPO_NAME)
        
        pass

if __name__ == '__main__':
    unittest.main()
