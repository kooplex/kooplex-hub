import sys
import getopt
import json
import socket
import string
import random
import docker
import requests as req

from time import sleep
from io import BytesIO
from kooplex.lib.libbase import LibBase
from kooplex.lib.libbase import get_settings

class Spawner(LibBase):
       
    def __init__(self, username, image=None, host=None, port=None):
        self.docker_host = get_settings('KOOPLEX_SPAWNER', 'docker_host', host)
        self.docker_port = get_settings('KOOPLEX_SPAWNER', 'docker_port', port)
        self.docker_network = get_settings('KOOPLEX_SPAWNER', 'docker_network', 'bridge')
        self.docker_container_prefix = get_settings('KOOPLEX_SPAWNER', 'docker_container_prefix', 'kooplex-jupyter')
        self.docker_image = get_settings('KOOPLEX_SPAWNER', 'docker_image', (image, 'kooplex-jupyter'))

        self.proxy_host = get_settings('KOOPLEX_SPAWNER', 'proxy_host', '127.0.0.1')
        self.proxy_port = get_settings('KOOPLEX_SPAWNER', 'proxy_port', 8000)
        self.proxy_path = get_settings('KOOPLEX_SPAWNER', 'proxy_path', 'hub/%s')
        self.proxy_api_port = get_settings('KOOPLEX_SPAWNER', 'proxy_api_port', 8001)
        
        self.spawner_port_pool = get_settings('KOOPLEX_SPAWNER', 'spawner_port_pool', [16000, 17000])
        
        self.username = username
        
        self.docli = self.create_docker_client()

    ### -------------------------------------------------------
    ### Docker setup

    def create_docker_client(self):
        if self.docker_host is None or self.docker_port is None:
            url = 'unix:///var/run/docker.sock'
        else:
            url = 'tcp://%s:%d' % (self.docker_host, self.docker_port)
        return docker.Client(base_url=url)

    def get_container_name():
        return '%s-%s' % (Spawner.docker_container_prefix, self.username)

    def ensure_image_exists(self):
        imgs = docli.images(name=self.docker_image)
        if imgs is None or len(imgs) == 0:
            docli.pull(self.docker_image)
        return docli.images(name=self.docker_image)

    def list_containers(self):
        containers = docli.containers(all=True)
        # TODO: modify to return user's containers only
        #containers = [ c for c in docli.containers() if Spawner.container_prefix in c['Names'][0] ]
        return containers

    def create_container(self):
        self.ensure_image_exists()
        name = self.get_container_name()
        container = docli.create_container(
            image=self.docker_image,
            detach=True,
            name=name,
            command=command,
            #entrypoint='start-notebook.sh --NotebookApp.base_url=/' + name
        )
        docli.disconnect_container_from_network(name, 'bridge')
        docli.connect_container_to_network(name, self.docker_network)
        return container

    def ensure_container_exists(self):
        name = self.get_container_name()
        conts = docli.containers(filters={'name': name})
        if conts is None or len(conts) == 0:
            self.create_container()
        return docli.containers(filters={'name': name})[0]

    def start_container(self):
        container = self.ensure_container_exists()
        docli.start(container)
        return container

    def ensure_container_running(self, name, command):
        name = self.get_container_name()
        container = self.ensure_container_exists()
        if container['status'] == 'Stopped':
            self.start_container()
        return docli.containers(filters={'name': name})[0]

    ### -------------------------------------------------------
    ### Proxy setup

    def create_route(self, path, host=None, port=None):
        path = self.proxy_path % path
        url = 'http://%s:%d/api/routes/%s' % (
            self.proxy_host,
            self.proxy_api_port,
            path)
        if host:
            data = json.dumps({
                'target': 'http://%s:%d/%s' % (
                    host, 
                    port,
                    path)
                })
            return url, data
        else:
            return url, None

    def add_route(self, path, host, port):
        url, data = self.create_route(path, host, port)
        res = self.http_post(url, data=data)

    def get_route(self, path):
        url, data = self.create_route(path)
        return self.http_get(url).json()

    def remove_route(self, path):
        url, data = self.create_route(path)
        res = self.http_delete(url)

    def get_external_url(self, path, port):
        url = 'http://%s/%s' % (
            self.proxy_external_host,
            path)
        return url

    ### -------------------------------------------------------
    ### Kernel spawner

    def get_random_port(self):
        return random.randint(self.spawner_port_pool[0], self.spawner_port_pool[1])

    def get_kernel_command(self):
        return 'start-notebook.sh --NotebookApp.base_url=/' + self.username

    def spawn_kernel(self, container_name, port):
        container = self.ensure_container_running(name)
        exec = docli.exec_create(
            name=container_name,
            cmd=self.get_kernel_command(),
            user=self.username)
        docli.exec_start(exec)
        add_proxy_rule()


    def spawn_container(self, container_name, command, port):
        """
        Simple function to spawn a container from an image.
        The container is connected to the same docker network
        as "poor man's binder" is.
        It is assumed that start-notebook.sh exists and
        can be run in the image as it will be our entry point.
        """

        # starting the container and connecting it to the
        # appropriate docker network
        docli.start(container)
        

        #proxy = Proxy()
        #rule = proxy.add_rule(container_name, port)
        rule = None

        return container, rule
