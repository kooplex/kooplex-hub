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
from kooplex.lib.libbase import LibBase
from kooplex.lib.libbase import get_settings
from kooplex.lib.smartdocker import Docker
from kooplex.lib.proxy import Proxy
from kooplex.hub.models import Notebook

class Spawner(LibBase):
       
    def __init__(self, username, container_name=None, image=None, proxy_path=None):
        self.username = username
        self.container_name = get_settings('KOOPLEX_SPAWNER', 'notebook_container_name', container_name, 'kooplex-notebook-{$username}')
        self.image = get_settings('KOOPLEX_SPAWNER', 'notebook_image', image, 'kooplex-notebook')
        self.proxy_path = get_settings('KOOPLEX_SPAWNER', 'notebook_proxy_path', proxy_path, '/notebook/{$username}/{$notebook.id}')
        self.ip_pool = get_settings('KOOPLEX_SPAWNER', 'notebook_ip_pool', None, ['172.18.20.1', '172.18.20.255'])
        self.port = get_settings('KOOPLEX_SPAWNER', 'notebook_port', None, 8000)
        self.service_path = get_settings('KOOPLEX_SPAWNER', 'service_path', None, '/srv/kooplex')
        
        self.docli = self.make_docker_client()
        self.pxcli = self.make_proxy_client()      

    def make_docker_client(self):
        return Docker()

    def make_proxy_client(self):
        return Proxy()

    def pick_random_ip(self):
        # TODO: modify to return available ip address
        # TODO: skip invalid addresses (.0, .255 etc)
        fromip = int(IPAddress(self.ip_pool[0]))
        toip = int(IPAddress(self.ip_pool[1]))
        ip = str(IPAddress(random.randint(fromip, toip)))
        return ip
    
    def get_container_name(self):
        name = self.container_name
        name = name.replace('{$username}', self.username)
        return name

    def get_proxy_path(self, id):
        path = self.proxy_path
        path = path.replace('{$username}', self.username)
        path = path.replace('{$notebook.id}', id)
        return path

    def get_external_url(self, path):
        url = self.pxcli.get_external_url(path)
        return url

    def make_notebook(self):
        id = str(uuid.uuid4())
        container_name = self.get_container_name()
        proxy_path = self.get_proxy_path(id)
        external_url = self.get_external_url(proxy_path)
        ip = self.pick_random_ip()

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
            proxy_path=proxy_path,
            external_url=external_url,
        )
        notebook.set_environment({
                'NB_USER': self.username,
                'NB_UID': 10002,     # TODO
                'NB_GID': 10002,     # TODO
                'NB_URL': proxy_path,
                'NB_PORT': self.port
            })
        notebook.set_binds({
                LibBase.join_path(self.service_path, 'notebook/etc/ldap/ldap.conf'): {
                    'bind': '/etc/ldap.conf',
                    'mode': 'rw'
                },
                LibBase.join_path(self.service_path, 'notebook/etc/nslcd.conf'): {
                    'bind': '/etc/nslcd.conf',
                    'mode': 'rw'
                    },
                LibBase.join_path(self.service_path, 'notebook/etc/nsswitch.conf'): {
                    'bind': '/etc/nsswitch.conf',
                    'mode': 'rw'
                    },
                LibBase.join_path(self.service_path, 'notebook/init'): {
                    'bind': '/init',
                    'mode': 'rw'
                    }
            })
        # TODO: make binds read-only once config is fixed
        notebook.set_ports([self.port])
        return notebook

    def get_notebook(self):
        notebooks = Notebook.objects.filter(username=self.username)
        if notebooks.count() > 0:
            return notebooks[0]
        else:
            return None

    def start_notebook(self, notebook):
        self.docli.ensure_container_running(notebook)
        self.pxcli.add_route(notebook.proxy_path, notebook.ip, notebook.port)
        notebook.save()
        return notebook

    def ensure_notebook_running(self):
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
        self.docli.ensure_container_removed(notebook)
        notebook.delete()

    def ensure_notebook_stopped(self):
        notebook = self.get_notebook()
        if not notebook:
            return
        else:
            container = self.docli.get_container(notebook)
            if not container:
                notebook.delete()
            else:
                self.stop_notebook(notebook)

    def start_kernel(self, notebook, kernel):
        raise NotImplementedError

    def stop_kernel(self, notebook, kernel):
        raise NotImplementedError