import re
import json
from docker.client import Client

from kooplex.lib import get_settings


class Docker:
    base_url = get_settings('docker', 'base_url')
    pattern_imagename = get_settings('docker', 'pattern_imagenamefilter')
    network = get_settings('docker', 'network')

    def __init__(self):
        self.client = Client(base_url = self.base_url)

    def list_imagenames(self):
        for image in self.client.images(all = True):
            for tag in image['RepoTags']:
                if re.match(self.pattern_imagenamefilter, tag):
                    _, imagename, _ = re.split(self.pattern_imagename_notebook, tag)
                    yield imagename

    def get_container(self, container):
        for item in self.client.containers(all = True):
            # docker API prepends '/' in front of container names
            if '/' + container.name in item['Names']:
                return item
        return None

 
    def create_container(self, container):
        volumes = container.get_volumes() #FIXME: [ '/etc/jupyter_notebook_config.py', ... ]
        binds = container.get_binds() #FIXME: {'/srv/kooplex/mnt_kooplex/kooplex/notebook/etc/jupyter_notebook_config.py': {'mode': 'rw', 'bind': '/etc/jupyter_notebook_config.py'}, ... }
        host_config = self.client.create_host_config(
            binds = binds,
            privileged = True
        )
        networking_config = container.get_networking_config() #FIXME
####    def get_networking_config(self):
####        networking_config = None
####        if self.network:
####            networking_config = {
####                'EndpointsConfig': {
####                    self.network: {}
####                    }
####               }
####            if self.ip:
####                networking_config['EndpointsConfig'][self.network] = {
####                        'IPAMConfig': {
####                            'IPv4Address': self.ip,
####                            #'IPv6Address': '...',
####                        }
####                    }
####        return networking_config
        if container.environment is None:
            environment = containser.environment = json.dumps(self.environment)
        else:
            environment = json.loads(container.environment)
        ports = [ 8000 ] #FIXME
        self.client.create_container(
            name = container.name,
            image = container.image.imagename,
            detach = True,
            hostname = container.name,
            host_config = host_config,
            networking_config = networking_config,
            command = container.command, #FIXME
            environment = environment,
            volumes = volumes,
            ports = ports
        )
        return self.get_container(container)

    def run_container(self, container):
        docker_container_info = self.get_container(container)
        if docker_container_info is None:
            docker_container_info = self.create_container(container)
