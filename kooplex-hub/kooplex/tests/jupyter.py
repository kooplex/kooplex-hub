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

    def make_notebook(self, spawner):
        assert isinstance(spawner, Spawner)

        nb = spawner.ensure_notebook_running()
        return nb

    def make_jupyter(self):
        sp = self.make_spawner()
        nb = self.make_notebook(sp)
        j = Jupyter(nb)
        return sp, nb, j

    def make_session(self, notebook):
        assert isinstance(notebook, Notebook)

        s = Session(
            notebook_path=Test_jupyter.TEST_NOTEBOOK_PATH,
            kernel_name=Test_jupyter.TEST_NOTEBOOK_KERNEL
        )
        return s

    def test_start_stop_session(self):
        sp, nb, j = self.make_jupyter()
        s = self.make_session(nb)
        s = j.start_session(s)
        
        j.stop_session(s)
        sp.ensure_notebook_stopped()


if __name__ == '__main__':
    unittest.main()
