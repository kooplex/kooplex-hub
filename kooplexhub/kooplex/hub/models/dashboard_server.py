import os
from django.db import models
from .modelbase import ModelBase

from kooplex.lib.libbase import get_settings

class Dashboard_server(models.Model, ModelBase):
    name = models.CharField(primary_key=True, max_length=200)
    id = models.CharField(max_length=200)
    docker_host = models.CharField(max_length=200, null=True)
    docker_port = models.IntegerField(null=True)
    image = models.CharField(max_length=200, null=True)
    network = models.CharField(max_length=200, null=True)
    ip = models.GenericIPAddressField()
    privileged = models.BooleanField(default=False)
    command = models.TextField(null=True)
    environment = models.TextField(null=True)
    binds = models.TextField(null=True)
    ports = models.IntegerField(null=True)
    state = models.CharField(max_length=15, null=True)
    project_owner = models.CharField(max_length=200, null=True)
    project_name = models.CharField(max_length=200, null=True)
    is_stopped = models.BooleanField(default=False)
    dir = models.CharField(max_length=200, null=True)
    url = models.CharField(max_length=200, null=True)
    cache_url = models.CharField(max_length=200, null=True)
    dashboard_name = models.CharField(max_length=200, null=True)
    kernel_gateway_name = models.CharField(max_length=200, null=True)
    type  = models.CharField(max_length=200, null=True)

    class Meta:
        db_table = "kooplex_hub_dasboard_server"

    def init(self, docker, dict):
        self.id = dict['Id']
        self.name = dict['Names'][0][1:]
        if docker:
            self.docker_host = docker.host
            if docker.port:
                self.docker_port = docker.port
            else:
                self.docker_port = 0
        self.image = dict['Image']
        try:
            self.network = list(dict['NetworkSettings']['Networks'].keys())[0]
            self.ip = dict['NetworkSettings']['Networks'][self.network]['IPAMConfig']['IPv4Address']
        except:
            self.ip = dict['NetworkSettings']['Networks'][self.network]['IPAddress']
        self.command = dict['Command']
        self.environment = None  # not returned by api
        self.volumes = None  # TODO
        self.ports = dict['Ports'][0]['PrivatePort']
        self.state = dict['State']  # created|restarting|running|paused|exited|dead
        prefix = get_settings('dashboards', 'prefix', None, '')
        self.type = self.image.split(prefix + "_dashboards-")[1]
        url_prefix = get_settings('dashboards', 'url_prefix', None, '')
        url_prefix = url_prefix.replace('{$dashboard_port}', str(self.ports))
        self.dir = get_settings('dashboards', 'dir', None, '')
        self.dir = self.dir.replace('{$image_postfix}', self.type)

        self.dashboard_name = dict['Names'][0][1:]
        self.kernel_gateway_name = self.dashboard_name.replace("dashboards-", "kernel-gateway-")

        outer_host = get_settings('hub', 'outer_host')
        proto = get_settings('hub', 'protocol')
        self.url = "%s://%s/%s/" % (proto, outer_host, url_prefix)
        self.cache_url = "%s/_api/cache/" % (self.url)


    def get_full_dir_to(self):
        srv_dir = get_settings('users', 'srv_dir')
        prefix = get_settings('dashboards', 'prefix', None, '')
        return os.path.join(srv_dir, prefix, self.dir)
