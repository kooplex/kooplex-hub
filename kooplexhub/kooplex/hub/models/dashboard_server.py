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
    dir_to = models.CharField(max_length=200, null=True)
    url = models.CharField(max_length=200, null=True)
    cache_url = models.CharField(max_length=200, null=True)
    dashboard_name = models.CharField(max_length=200, null=True)
    kernel_gateway_name = models.CharField(max_length=200, null=True)

    class Meta:
        db_table = "kooplex_hub_dasboard_server"

    def from_docker_dict(docker, dict):
        c = Dashboard_server()
        c.id = dict['Id']
        c.name = dict['Names'][0][1:]
        if docker:
            c.docker_host = docker.host
            if docker.port:
                c.docker_port = docker.port
            else:
                c.docker_port = 0
        c.image = dict['Image']
        try:
            c.network = list(dict['NetworkSettings']['Networks'].keys())[0]
            c.ip = dict['NetworkSettings']['Networks'][c.network]['IPAMConfig']['IPv4Address']
        except:
            c.ip = dict['NetworkSettings']['Networks'][c.network]['IPAddress']
        c.command = dict['Command']
        c.environment = None  # not returned by api
        c.volumes = None  # TODO
        c.ports = dict['Ports'][0]['PrivatePort']
        c.state = dict['State']  # created|restarting|running|paused|exited|dead

        prefix = get_settings('dashboards', 'prefix', None, '')

        url_prefix = get_settings('dashboards', 'url_prefix', None, '')
        url_prefix = url_prefix.replace('{$dashboard_port}', str(55))
        c.dir_to = get_settings('dashboards', 'dir_to', None, '')
        c.dir_to = c.dir_to.replace('{$image_postfix}', c.image)
        c.dashboard_name = dict['Names'][0][1:]
        c.kernel_gateway_name = c.dashboard_name.replace("dashboards-", "kernel-gateway-")

        outer_host = get_settings('hub', 'outer_host')
        proto = get_settings('hub', 'protocol')
        c.url = "%s://%s/%s/" % (proto, outer_host, url_prefix)
        c.cache_url = "%s/_api/cache/" % (c.url)
        return c
