import sys
import getopt
import json
import string
import uuid
import random
import docker
import requests as req
from os import path
from netaddr import IPAddress
from time import sleep
from io import BytesIO

from kooplex.lib.libbase import LibBase, get_settings
from kooplex.lib.restclient import RestClient
from kooplex.lib.smartdocker import Docker
from kooplex.lib.proxy import Proxy
from kooplex.lib.jupyter import Jupyter
from kooplex.hub.models import Container, Notebook, Session

from kooplex.lib.debug import *
DEBUG = True

class Spawner(RestClient):
       
    def __init__(self, username, project_owner=None, project_name=None, container_name=None, image=None):
        print_debug(DEBUG,"")
        self.username = username
        self.project_owner = project_owner
        self.project_name = project_name
        prefix = get_settings('prefix', 'name')
        self.container_name = get_settings('spawner', 'notebook_container_name', container_name, prefix+'-notebook-{$username}')
        self.image = get_settings('spawner', 'notebook_image', image, prefix + '-notebook')
        self.notebook_path = get_settings('spawner', 'notebook_proxy_path', None, '/notebook/{$username}/{$notebook.id}')
        self.session_path = get_settings('spawner', 'session_proxy_path', None, '/notebook/{$username}/{$notebook.id}/tree/{$username}/{$session.notebook_path}')
        self.ip_pool = get_settings('spawner', 'notebook_ip_pool', None, ['172.18.20.1', '172.18.20.255'])
        self.port = get_settings('spawner', 'notebook_port', None, 8000)
        self.srv_path = get_settings('spawner', 'srv_path', None, '/srv/' + prefix)
        
        self.docli = self.make_docker_client()
        self.pxcli = self.make_proxy_client()

    def make_docker_client(self):
        print_debug(DEBUG,"")
        return Docker()

    def make_proxy_client(self):
        return Proxy()

    def pick_random_ip(self):
        print_debug(DEBUG,"")
        # TODO: modify to return available ip address
        # TODO: skip invalid addresses (.0, .255 etc)
        fromip = int(IPAddress(self.ip_pool[0]))
        toip = int(IPAddress(self.ip_pool[1]))
        ip = str(IPAddress(random.randint(fromip, toip)))
        return ip
    
    def get_container_name(self):
        print_debug(DEBUG,"")
        name = self.container_name
        name = name.replace('{$username}', self.username)
        name = name.replace('{$project_owner}', self.project_owner)
        name = name.replace('{$project_name}', self.project_name)
        return name

    def get_external_url(self, path):
        print_debug(DEBUG,"")
        url = self.pxcli.get_external_url(path)
        return url

    def append_ldap_binds(self, binds, svc):
        print_debug(DEBUG,"")
        basepath = LibBase.join_path(self.srv_path, svc)
        binds[LibBase.join_path(basepath, 'etc/ldap/ldap.conf')] = {'bind': '/etc/ldap/ldap.conf', 'mode': 'rw'}
        binds[LibBase.join_path(basepath, 'etc/nslcd.conf')] = {'bind': '/etc/nslcd.conf', 'mode': 'rw'}
        binds[LibBase.join_path(basepath, 'etc/nsswitch.conf')] = {'bind': '/etc/nsswitch.conf', 'mode': 'rw'}

    def append_home_binds(self, binds, svc):
        print_debug(DEBUG,"")
        #container_home=LibBase.join_path('/home', self.username + '/' + self.project_name)
        host_home = '/home/' + self.username
        container_home = '/home/' + self.username
        binds[LibBase.join_path(self.srv_path, host_home)] = {'bind': container_home, 'mode': 'rw'}

    def append_ownclouddata_binds(self, binds, svc):
        print_debug(DEBUG,"")
        container_data_home = LibBase.join_path('/home', self.username + '/projects/' + 'data')
        host_data_path = 'ownCloud/' + self.username + '/files'
        binds[LibBase.join_path(self.srv_path, host_data_path)] = {'bind': container_data_home, 'mode': 'rw'}

    def append_init_binds(self, binds, svc):
        print_debug(DEBUG,"")
        basepath = LibBase.join_path(self.srv_path, svc)
        binds[LibBase.join_path(basepath, '/init')] = {'bind': '/init', 'mode': 'rw'}

    def get_notebook_path(self, id):
        print_debug(DEBUG,"")
        path = self.notebook_path
        path = path.replace('{$username}', self.username)
        path = path.replace('{$notebook.id}', id)
        return path

    def make_notebook(self):
        print_debug(DEBUG,"")
        id = str(uuid.uuid4())
        container_name = self.get_container_name()
        notebook_path = self.get_notebook_path(id)
        external_url = self.get_external_url(notebook_path)
        ip = self.pick_random_ip()
        binds = {}
        self.append_ldap_binds(binds, 'notebook')
        self.append_home_binds(binds, 'notebook')
        self.append_ownclouddata_binds(binds, 'notebook')
        self.append_init_binds(binds, 'notebook')
        # TODO: remove hardcoding!
        binds[LibBase.join_path(self.srv_path, 'notebook/etc/jupyter_notebook_config.py')] = {'bind': '/etc/jupyter_notebook_config.py', 'mode': 'rw' }
        notebook = Notebook(
            id=id,
            docker_host=self.docli.host,
            docker_port=self.docli.port,
            name=container_name,
            image=self.image,
            network=self.docli.network,
            ip=ip,
            privileged=True,
            command=None,
            username=self.username,
            port=self.port,
            proxy_path=notebook_path,
            external_url=external_url,
            project_owner=self.project_owner,
            project_name = self.project_name,
            is_stopped=False,
        )
        notebook.set_environment({
                'NB_USER': self.username,
                'NB_UID': 10002,     # TODO
                'NB_GID': 10002,     # TODO
                'NB_URL': notebook_path,
                'NB_PORT': self.port
            })
        #print(notebook_path)
        notebook.set_binds(binds)
        # TODO: make binds read-only once config is fixed
        notebook.set_ports([self.port])
        #print('notebookrunnng')
        return notebook

    def get_notebook(self):
        print_debug(DEBUG,"")
        notebooks = Notebook.objects.filter(
            username=self.username,
            image=self.image,
            project_owner=self.project_owner,
            project_name=self.project_name,)
            #image = self.image)
        if notebooks.count() > 0:
            # TODO: verify if container is there and proxy works
            return notebooks[0]
        else:
            return None

    def start_notebook(self, notebook):
        print_debug(DEBUG,"")
        self.docli.ensure_container_running(notebook)
        #print('container running')
        notebook.is_stopped = False
        self.pxcli.add_route(notebook.proxy_path, notebook.ip, notebook.port)
        #print('proxy running')
        notebook.save()
        return notebook

    def ensure_notebook_running(self):
        print_debug(DEBUG,"")
        notebook = self.get_notebook()
        if not notebook:
            notebook = self.make_notebook()
            notebook = self.start_notebook(notebook)
        else:
            # TODO: verify if accessible, restart if necessary
            container = self.docli.get_container(notebook)
            if not container:
                notebook.delete()
                notebook = self.make_notebook()
                notebook = self.start_notebook(notebook)
            elif container.state != 'running':
                self.docli.ensure_container_removed(container)
                notebook.delete()
                notebook = self.make_notebook()
                notebook = self.start_notebook(notebook)
        return notebook

    def stop_notebook(self, notebook):
        print_debug(DEBUG,"")
        self.docli.ensure_container_stopped(notebook)
        notebook.is_stopped=True
        print(notebook.proxy_path)
        self.pxcli.remove_route(notebook.proxy_path)
        notebook.save()

    def delete_notebook(self, notebook):
        print_debug(DEBUG,"")
        self.docli.ensure_container_removed(notebook)
        notebook.delete()

    def ensure_notebook_stopped(self):
        print_debug(DEBUG,"")
        notebook = self.get_notebook()
        if notebook:
            self.stop_notebook(notebook)
        else:
            # Try to stop container if running but not in DB
            notebook = self.make_notebook()
            self.docli.ensure_container_removed(notebook)

    def get_session_path(self, notebook, session):
        print_debug(DEBUG,"")
        path = self.session_path
        path = path.replace('{$username}', self.username)
        path = path.replace('{$notebook.id}', str(notebook.id))
        path = path.replace('{$session.notebook_path}', session.notebook_path)
        return path

    def make_session(self, notebook_path, kernel):
        print_debug(DEBUG,"")
        session = Session(
            notebook_path=notebook_path,
            kernel_name=kernel,
        )
        return session

    def start_session(self, notebook_path, kernel, repo_name, container_name, is_forked=False, project_id=0, target_id=0):
        print_debug(DEBUG,"")
        notebook = self.ensure_notebook_running()
        session = self.make_session(notebook_path, kernel)
        jpcli = Jupyter(notebook)
        session = jpcli.start_session(session)
        proxy_path = self.get_session_path(notebook, session)
        session.external_url = self.get_external_url(proxy_path)
        session.is_forked = is_forked
        session.project_id = project_id
        session.target_id = target_id
        session.repo_name = repo_name
        session.container_name = container_name
        session.save()
        return session


    def stop_session(self, session):
        print_debug(DEBUG,"")
        jpcli = Jupyter(session.notebook)
        jpcli.stop_session(session)

    def list_sessions(self, container):
        print_debug(DEBUG,"")
        raise NotImplementedError
        