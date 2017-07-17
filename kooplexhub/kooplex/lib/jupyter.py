from kooplex.lib.libbase import LibBase
from kooplex.lib.libbase import get_settings
from kooplex.lib.restclient import RestClient

from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session
from kooplex.lib.debug import *

class JupyterError(Exception):
    pass

class Jupyter(RestClient):
    """Jupyter notebook api client.
    based on: https://gist.github.com/blink1073/ecae5130dfe138ea2aff
    """
    token = "aiSiga1aiFai2AiZu1veeWein5gijei8yeLay2Iecae3ahkiekeisheegh2ahgee"

    def __init__(self, notebook):
        print_debug("")
        assert isinstance(notebook, Notebook)
        self.notebook = notebook
        # TODO: use external URL for debug but otherwise could just
        # switch to internal IP addresses and bypass the proxy
        base_url = get_settings('session', 'base_url', None, '')
        RestClient.__init__(self, base_url=base_url)

    def http_prepare_url(self, path):
        print_debug("")
        url = LibBase.join_path(self.base_url, self.notebook.proxy_path)
        url = LibBase.join_path(url, '/api')
        url = LibBase.join_path(url, path)
        return url

    def http_prepare_headers(self, headers):
        print_debug("")
        headers = RestClient.http_prepare_headers(self, headers)
        headers['Authorization'] = "token %s" % self.token
        return headers
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

    def make_empty_notebook_python3(self):
        return {
            "cells": [{
                "cell_type": "code",
                "execution_count": None,
                "metadata": {
                    "collapsed": True
                },
                "outputs": [],
                "source": []
            }],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3"
                },
                "language_info": {
                    "codemirror_mode": {
                        "name": "ipython",
                        "version": 3
                    },
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.5.1"
                }
            },
            "nbformat": 4,
            "nbformat_minor": 0
        }

    def create_notebook(self, name):
        print_debug("")
        return self.upload_file(name, name, 'notebook', 'json', self.make_empty_notebook_python3())

    def upload_file(self, path, name=None, type=None, format=None, content=None):
        print_debug("")
        data = {
            'name': name,
            'path': path,
            'type': type,
            'format': format,
            'content': content
        }
        res = self.http_put('/contents/%s' % path, data=data, expect=[200, 201])
        return res.json()

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
        print_debug("")
        assert isinstance(session, Session)

        data = session.to_jupyter_dict()
        res = self.http_post('/sessions', data=data)
        print(res)
        session = Session.from_jupyter_dict(self.notebook, res.json())
        session.notebook = self.notebook
        return session

    def stop_session(self, session):
        print_debug("")
        assert isinstance(session, Session)

        self.http_delete('/sessions/%s' % session.id)
        session.delete()

    def get_session(self, session):
        print_debug("")
        assert isinstance(session, Session)

        res = self.http_get('/sessions/%s' % session)
        return res.json()

    def rename_session(self, path, newpath):
        print_debug("")
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
        print_debug("")
        res = self.http_get('/sessions')
        return res.json()

    # Kernels

    def list_kernels(self):
        print_debug("")
        res = self.http_get('/kernels')
        return res.json()

    def start_kernel(self, name):
        print_debug("")
        params = {'name': name}
        res = self.http_post('/kernels', data=data)
        return res.json()

    def get_kernel(self, kernel_id):
        print_debug("")
        res = self.http_get('/kernels/%s' % kernel_id)
        return res.json()

    def stop_kernel(self, kernel_id):
        print_debug("")
        self.http_delete('/kernels/%s' % kernel_id)

    def interrupt_kernel(self, kernel_id):
        print_debug("")
        self.http_post('/kernels/%s/interrupt' % kernel_id)

    def restart_kernel(self, kernel_id):
        print_debug("")
        self.http_post('/kernels/%s/restart' % kernel_id)

    # Kernel Specifications

    def list_kernelspecs(self):
        print_debug("")
        res = self.http_get('/kernelspecs')
        return res.json()

    # Configs

    def get_config_section(self, name):
        # GET /config/{section_name}
        pass

    def update_config_section(self, name, config):
        # PATCH /config/{section_name}
        pass
