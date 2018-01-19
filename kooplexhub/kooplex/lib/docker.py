"""
@author: Jozsef Steger, David Visontai
@summary: docker API driver
"""
import logging
import os
import re
import json
from docker.client import Client

from kooplex.lib import get_settings

logger = logging.getLogger(__name__)

class Docker:
    base_url = get_settings('docker', 'base_url')
    pattern_imagenamefilter = get_settings('docker', 'pattern_imagenamefilter')
    network = get_settings('docker', 'network')

    def __init__(self):
        self.client = Client(base_url = self.base_url)
        logger.debug("Client init")

    def list_imagenames(self):
        logger.debug("Listing imagenames")
        for image in self.client.images(all = True):
            if image['RepoTags'] is None:
                continue
            for tag in image['RepoTags']:
                if re.match(self.pattern_imagenamefilter, tag):
                    _, imagename, _ = re.split(self.pattern_imagenamefilter, tag)
                    logger.debug("Found image: %s" % imagename)
                    yield imagename

    def get_container(self, container):
        for item in self.client.containers(all = True):
            # docker API prepends '/' in front of container names
            if '/' + container.name in item['Names']:
                logger.debug("Get container %s"%container.name)
                return item
        return None

    def create_container(self, container, volumemapping):
        volumes = []    # the list of mount points in the container
        binds = {}      # a mapping dictionary of the container mounts
        # the bare minimum like for a notebook: home, git and share folders
        for vol, mp, mode in volumemapping:
            volumes.append(mp)
            binds[vol] = { 'bind': mp, 'mode': mode }
        # additional volumes specified by the owner
        for volume in container.volumes:
            mp = os.path.join('/vol', volume.name)
            volumes.append(mp)
            binds[volume.name] = { 'bind': mp, 'mode': 'rw' } #FIXME: should come from model
        host_config = self.client.create_host_config(
            binds = binds,
            privileged = True
        )
        networking_config = { 'EndpointsConfig': { self.network: {} } }
        ports = [ 8000 ] #FIXME
        if container.environment is None:
            environment = containser.environment = json.dumps(self.environment)
        else:
            environment = json.loads(container.environment)
        self.client.create_container(
            name = container.name,
            image = container.image.imagename,
            detach = True,
            hostname = container.name,
            host_config = host_config,
            networking_config = networking_config,
        #    command = container.command, #for notebook it is not set
            environment = environment,
            volumes = volumes,
            ports = ports
        )
        logger.debug("Container created")
        return self.get_container(container)

    def run_container(self, container, volumemapping):
        docker_container_info = self.get_container(container)
        if docker_container_info is None:
            logger.debug("Container did not exist, Creating new one")
            docker_container_info = self.create_container(container, volumemapping)
        container_state = docker_container_info['Status']
        if container_state == 'Created' or container_state.startswith('Exited'):
            logger.debug("Starting container")
            self.start_container(container)

    def start_container(self, container):
        self.client.start(container.name)
        # we need to retrieve the container state after starting it
        docker_container_info = self.get_container(container)
        container_state = docker_container_info['State']
        logger.debug("Container state %s" % container_state)
        assert container_state == 'running', "Container failed to start: %s" % docker_container_info

    def stop_container(self, container):
        self.client.stop(container.name)
        logger.debug("Container stopped %s"% container.name)


    def execute(self, container, command):
        execution = self.client.exec_create(container = container.name, cmd = command)
        return self.client.exec_start(execution, detach = False)

