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

class Spawner(LibBase):
       
    def __init__(self, username, image=None, host=None, port=None):
        self.docker_host = get_settings('KOOPLEX_SPAWNER', 'docker_host', host)
        self.docker_port = get_settings('KOOPLEX_SPAWNER', 'docker_port', port)
        self.docker_network = get_settings('KOOPLEX_SPAWNER', 'docker_network', 'bridge')
        self.docker_container_prefix = get_settings('KOOPLEX_SPAWNER', 'docker_container_prefix', 'kooplex-jupyter')
        self.docker_image = get_settings('KOOPLEX_SPAWNER', 'docker_image', (image, 'jupyter/minimal-notebook')) # TODO: replace with our image

        self.proxy_host = get_settings('KOOPLEX_SPAWNER', 'proxy_host', '127.0.0.1')
        self.proxy_port = get_settings('KOOPLEX_SPAWNER', 'proxy_port', 8000)
        self.proxy_path = get_settings('KOOPLEX_SPAWNER', 'proxy_path', 'hub/%s/%s')
        self.proxy_api_port = get_settings('KOOPLEX_SPAWNER', 'proxy_api_port', 8001)
        self.proxy_external_url = get_settings('KOOPLEX_SPAWNER', 'proxy_external_url', 'http://localhost/')
        
        self.spawner_ip_pool = get_settings('KOOPLEX_SPAWNER', 'spawner_ip_pool', ['172.17.20.1', '172.17.20.255'])
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

    def get_network(self):
        nets = self.docli.networks(names = (self.docker_network,))
        if nets and len(nets) == 1:
            return nets[0]
        else:
            return None

    def get_image(self):
        imgs = self.docli.images(name=self.docker_image)
        if imgs and len(imgs) == 1:
            return imgs[0]
        else:
            return None

    def pull_image(self):
        self.docli.pull(self.docker_image)
        return self.get_image()

    def build_image(self):
        raise NotImplementedError

    def ensure_image_exists(self):
        img = self.get_image()
        if img is None:
            img = self.pull_image()
        return img

    def get_container(self, name):
        conts = self.docli.containers(all=True,
            filters={
            'name': name,
            })
        if conts and len(conts) == 1:
            return conts[0]
        else:
            return None

    def list_containers(self):
        containers = docli.containers(all=True)
        # TODO: modify to return user's containers only
        #containers = [ c for c in docli.containers() if
        #Spawner.container_prefix in c['Names'][0] ]
        return containers

    def create_container(self, name):
        self.ensure_image_exists()
        container = self.docli.create_container(image=self.docker_image,
            detach=True,
            name=name,
            #command=command,
            #entrypoint='start-notebook.sh --NotebookApp.base_url=/' + name
        )
        self.docli.disconnect_container_from_network(name, 'bridge')
        self.docli.connect_container_to_network(name, self.docker_network)
        return self.get_container(name)

    def ensure_container_exists(self, name):
        cont = self.get_container(name)
        if cont is None:
            cont = self.create_container(name)
        return cont

    def start_container(self, name):
        container = self.ensure_container_exists(name)
        self.docli.start(container)
        return self.get_container(name)

    def ensure_container_running(self, name):
        container = self.ensure_container_exists(name)
        # created|restarting|running|paused|exited|dead
        if container['State'] in ('created', 'exited') :
            container = self.start_container(name)
        return container

    def stop_container(self, name):
        self.docli.stop(container=name)

    def kill_container(self, name):
        self.docli.kill(container=name)

    def ensure_container_stopped(self, name):
        container = self.get_container(name)
        if container:
            self.stop_container(name)

    def remove_container(self, name):
        self.docli.remove_container(name)

    def ensure_container_removed(self, name):
        container = self.get_container(name)
        if container:
            self.ensure_container_stopped(name)
            self.remove_container(name)

    def exec_container(self, name, command):
        exec = self.docli.exec_create(container=name, cmd=command, user=self.username)
        self.docli.exec_start(exec)

    ### -------------------------------------------------------
    ### Proxy setup

    def create_route(self, path, host=None, port=None):
        url = 'http://%s:%d/api/routes/%s' % (self.proxy_host,
            self.proxy_api_port,
            path)
        if host:
            data = json.dumps({
                'target': 'http://%s:%d/%s' % (host, 
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
        url = 'http://%s/%s' % (self.proxy_external_host,  path)
        return url

    ### -------------------------------------------------------
    ### Kernel spawner

    def get_random_port(self):
        # TODO: modify to find available port
        return random.randint(self.spawner_port_pool[0], self.spawner_port_pool[1])

    def get_kernel_container(self):
        return '%s-%s' % (self.docker_container_prefix, self.username)

    def get_kernel_path(self, id):
        return self.proxy_path % (self.username, id)

    def get_kernel_command(self, path, port):
        command = 'start-notebook.sh --NotebookApp.base_url=/%s --NotebookApp.port=%d' % (path, port)
        return command

    def get_external_url(self, path):
        url = self.proxy_external_url + path
        return url

    def get_kernel_info(self, username, id, host, container, port, path, url):
        data = json.dumps({
            'id': id,
            'host': host,
            'container': container,
            'port': port,
            'path': path,
            'url': url
        })
        return data

    def spawn_kernel(self):
        id = str(uuid.uuid4())
        host = self.docker_host
        port = self.get_random_port()
        container = self.get_kernel_container()
        path = self.get_kernel_path(id)
        command = self.get_kernel_command(path, port)
        url = self.get_external_url(path)
        
        self.ensure_container_running(container)
        self.exec_container(container, command)
        
        self.remove_route(path)
        self.add_route(path, host, port)

        return self.get_kernel_info(self.username, id, host, container, port, path, url)

    def kill_kernel(self):
        raise NotImplementedError
