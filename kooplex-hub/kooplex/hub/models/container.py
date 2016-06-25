import json
from django.db import models

from kooplex.lib.modelbase import ModelBase

class Container(models.Model, ModelBase):
    id =  models.UUIDField(primary_key=True)
    docker_host = models.URLField()
    docker_port = models.URLField()
    name = models.CharField(max_length=200)
    image = models.CharField(max_length=200)
    network = models.CharField(max_length=200)
    ip = models.GenericIPAddressField()
    command = models.TextField()
    environment = models.TextField()
    volumes = models.TextField()
    ports = models.TextField()
    state = models.CharField(max_length=15)

    def from_docker_dict(docker, dict):
        c = Container()
        c.id=dict['Id']
        c.name=dict['Names'][0][1:]
        if docker:
            c.docker_host = docker.host
            c.docker_port = docker.port
        c.image=dict['Image']
        try:
            c.network = list(dict['NetworkSettings']['Networks'].keys())[0]
            c.ip = dict['NetworkSettings']['Networks'][c.network]['IPAMConfig']['IPv4Address']
        except:
            pass
        c.command = dict['Command']
        c.environment = None    # not returned by api
        c.volumes = None        # TODO
        c.ports = None          # TODO
        c.state = dict['State']    # created|restarting|running|paused|exited|dead
        return c

    def get_environment(self):
        return self.load_json(self.environment)

    def set_environment(self, value):
        self.environment = self.save_json(value)

    def get_volumes(self):
        return self.load_json(self.volumes)

    def set_volumes(self, value):
        self.volumens = self.save_json(value)

    def get_ports(self):
        return self.load_json(self.ports)

    def set_ports(self, value):
        self.ports = self.save_json(value)

    def get_host_config(self):
        host_config = {}
        return host_config

    def get_networking_config(self):
        networking_config = None
        if not self.network:
            networking_config = {
                'EndpointsConfig': {
                    self.network: {}
                    }
                }
            if not self.ip:
                networking_config['EndpointsConfig'][self.network] = {
                        'IPAMConfig': {
                            'IPv4Address': self.ip,
                            #'IPv6Address': '...',
                        }
                    }
        return networking_config