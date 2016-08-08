import unittest
from kooplex.lib.spawner import Spawner
from kooplex.lib.jupyter import Jupyter
from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session

class Test_jupyter(unittest.TestCase):
    
    TEST_USERNAME = 'test'
    TEST_NOTEBOOK_PATH = 'notebooks/test.ipynb'
    TEST_NOTEBOOK_KERNEL = 'python3'

    def make_spawner(self):
        sp = Spawner(username=Test_jupyter.TEST_USERNAME)
        return sp

    def make_jupyter(self):
        sp = self.make_spawner()
        sp.ensure_notebook_stopped()
        nb = sp.ensure_notebook_running()
        j = j = Jupyter(nb)
        return sp, nb, j

    def test_start_stop_session(self):
        sp, nb, j = self.make_jupyter()
        s = sp.make_session(
            Test_jupyter.TEST_NOTEBOOK_PATH,
            Test_jupyter.TEST_NOTEBOOK_KERNEL)
        s = j.start_session(s)
        j.stop_session(s)
        sp.ensure_notebook_stopped()

    def test_create_notebook(self):
        sp, nb, j = self.make_jupyter()
        j.create_notebook('test.ipynb')

if __name__ == '__main__':
    unittest.main()
