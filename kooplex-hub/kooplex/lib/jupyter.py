from kooplex.lib.libbase import LibBase
from kooplex.lib.libbase import get_settings
from kooplex.lib.restclient import RestClient

from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session

class JupyterError(Exception):
    pass

class Jupyter(RestClient):
    """Jupyter notebook api client.
    based on: https://gist.github.com/blink1073/ecae5130dfe138ea2aff
    """
    
    def __init__(self, notebook):
        assert isinstance(notebook, Notebook)

        self.notebook = notebook
        # TODO: use external URL for debug but otherwise could just
        # switch to internal IP addresses and bypass the proxy
        base_url = notebook.external_url
        RestClient.__init__(self, base_url=base_url)

    def http_prepare_url(self, path):
        url = LibBase.join_path(self.base_url, '/api')
        url = LibBase.join_path(url, path)
        return url

    # Contents

    def list_contents(self, path, type, format, content):
        # GET /contents/{path}
        pass

    def copy_content(self, copy_from, ext, type):
        # POST /contents/{path}
        pass

    def rename_content(self, path, newpath):
        # PATCH /contents/{path}
        pass

    def create_content(self, path, name, newpath, type, format, content):
        # PUT /contents/{path}
        pass

    def delete_content(self, path):
        # DELETE /contents/{path}
        path

    # Checkpoints

    def list_checkpoints(self, path):
        # GET /contents/{path}/checkpoints
        pass

    def create_checkpoint(self, path):
        # POST /contents/{path}/checkpoints
        pass

    def restore_checkpoint(self, path, checkpoint_id):
        # POST /contents/{path}/checkpoints/{checkpoint_id}
        pass

    def delete_checkpoint(self, path, checkpoint_id):
        # DELETE /contents/{path}/checkpoints/{checkpoint_id}
        pass

    # Sessions

    def start_session(self, session):
        assert isinstance(session, Session)

        data = session.to_jupyter_dict()
        res = self.http_post('/sessions', data=data)
        session = Session.from_jupyter_dict(self.notebook, res.json())
        session.notebook = self.notebook
        session.save()
        return session

    def stop_session(self, session):
        assert isinstance(session, Session)

        self.http_delete('/sessions/%s' % session.id)
        session.delete()

    def get_session(self, session):
        assert isinstance(session, Session)

        res = self.http_get('/sessions/%s' % session)
        return res.json()

    def rename_session(self, path, newpath):
        assert isinstance(session, Session)

        data = {
            'model': {
                'notebook': {
                    'path': path
                }
            }
        }
        res = self.http_patch('/sessions/%s' % create_session, data=data)
        return res.json()

    def list_sessions(self):
        res = self.http_get('/sessions')
        return res.json()

    # Kernels

    def list_kernels(self):
        res = self.http_get('/kernels')
        return res.json()

    def start_kernel(self, name):
        params = {'name': name}
        res = self.http_post('/kernels', data=data)
        return res.json()

    def get_kernel(self, kernel_id):
        res = self.http_get('/kernels/%s' % kernel_id)
        return res.json()

    def stop_kernel(self, kernel_id):
        self.http_delete('/kernels/%s' % kernel_id)

    def interrupt_kernel(self, kernel_id):
        self.http_post('/kernels/%s/interrupt' % kernel_id)

    def restart_kernel(self, kernel_id):
        self.http_post('/kernels/%s/restart' % kernel_id)

    # Kernel Specifications

    def list_kernelspecs(self):
        res = self.http_get('/kernelspecs')
        return res.json()

    # Configs

    def get_config_section(self, name):
        # GET /config/{section_name}
        pass

    def update_config_section(self, name, config):
        # PATCH /config/{section_name}
        pass
