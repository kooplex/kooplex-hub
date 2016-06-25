import sys
import getopt
import json
import string
import uuid
import random
import docker
import requests as req

from netaddr import IPAddress
from time import sleep
from io import BytesIO
from kooplex.lib.libbase import LibBase
from kooplex.lib.libbase import get_settings
from kooplex.lib.docker import Docker
from kooplex.lib.proxy import Proxy
from kooplex.hub.models import Notebook

class Spawner(LibBase):
       
    def __init__(self, username, image=None):
        self.username = username
        self.notebook_container_name = get_settings('KOOPLEX_SPAWNER', 'notebook_container_prefix', 'kooplex-notebook-{$username}')
        self.notebook_image = get_settings('KOOPLEX_SPAWNER', 'notebook_image', image, 'kooplex-notebook')
        self.notebook_ip_pool = get_settings('KOOPLEX_SPAWNER', 'notebook_ip_pool', ['172.18.20.1', '172.18.20.255'])
        self.notebook_port = get_settings('KOOPLEX_SPAWNER', 'notebook_port', 8000)
        self.notebook_proxy_path = get_settings('KOOPLEX_SPAWNER', 'notebook_proxy_path', '/notebook/{$username}/{$notebook}')
        
        self.docli = self.make_docker_client()
        self.pxcli = self.make_proxy_client()      

    def make_docker_client(self):
        return Docker()

    def make_proxy_client(self):
        return Proxy()

    def pick_random_ip(self):
        # TODO: modify to return available ip address
        # TODO: skip invalid addresses (.0, .255 etc)
        fromip = int(IPAddress(self.notebook_ip_pool[0]))
        toip = int(IPAddress(self.notebook_ip_pool[1]))
        ip = str(IPAddress(random.randint(fromip, toip)))
        return ip
    
    def get_container_name(self):
        name = self.notebook_container_prefix
        name = name.replace('{$username}', self.username)
        return name

    def get_proxy_path(self, notebook):
        path = self.notebook_proxy_path
        path = path.replace('{$username}', self.username)
        path = path.replace('{$notebook}', notebook.id)
        return path

    def get_external_url(self, path):
        url = pxcli.get_external_url(path)
        return url

    def make_notebook(self):
        id = str(uuid.uuid4())
        container = self.get_container_name()
        path = self.get_proxy_path(id)
        url = self.get_external_url(path)
        ip = self.pick_random_ip()

        notebook = Notebook(
            id=id,
            username=self.username,
            host=self.docker_host,
            ip=ip,
            port=self.notebook_port,
            image=self.notebook_image,
            container=container,
            path=path,
            url=url,
        )
        return notebook


    def start_notebook(self, notebook):
        container = docli.ensure_container_running(notebook.container, notebook.image, notebook.ip)
        pxcli.add_route(notebook.path, notebook.ip, notebook.port)
        
        notebook.ip = self.get_container_ip(notebook.container)
        notebook.save()

