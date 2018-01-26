"""
@author: Jozsef Steger, David Visontai
@summary: docker API driver
"""
import logging
import re
import json
import shlex
from docker.client import Client

from kooplex.lib import get_settings

logger = logging.getLogger(__name__)

class Docker:
    base_url = get_settings('docker', 'base_url')
    network = get_settings('docker', 'network')

    def __init__(self):
        self.client = Client(base_url = self.base_url)
        logger.debug("Client init")

    def list_imagenames(self):
        logger.debug("Listing imagenames")
        pattern_imagenamefilter = get_settings('docker', 'pattern_imagenamefilter')
        for image in self.client.images(all = True):
            if image['RepoTags'] is None:
                continue
            for tag in image['RepoTags']:
                if re.match(pattern_imagenamefilter, tag):
                    _, imagename, _ = re.split(pattern_imagenamefilter, tag)
                    logger.debug("Found image: %s" % imagename)
                    yield imagename

    def list_volumenames(self):
        logger.debug("Listing volumenames")
        volumes = self.client.volumes()
        pattern_volnamefilter_functional = get_settings('volumes', 'pattern_functionalvolumenamefilter')
        pattern_volnamefilter_storage = get_settings('volumes', 'pattern_storagevolumenamefilter')
        for volume in volumes['Volumes']:
            volname_full = volume['Name']
            if re.match(pattern_volnamefilter_functional, volname_full):
                _, volname, _ = re.split(pattern_volnamefilter_functional, volname_full)
                logger.debug("Found functional volume: %s" % volname)
                yield { 'volumetype': 'functional', 'name': volname }
            elif re.match(pattern_volnamefilter_storage, volname_full):
                _, volname, _ = re.split(pattern_volnamefilter_storage, volname_full)
                logger.debug("Found storage volume: %s" % volname)
                yield { 'volumetype': 'storage', 'name': volname }

    def get_container(self, container):
        for item in self.client.containers(all = True):
            # docker API prepends '/' in front of container names
            if '/' + container.name in item['Names']:
                logger.debug("Get container %s" % container.name)
                return item
        return None

    def create_container(self, container):
        volumes = []    # the list of mount points in the container
        binds = {}      # a mapping dictionary of the container mounts
        # the bare minimum like for a notebook: home, git and share folders
        for vol, mp, mode in container.volumemapping:
            volumes.append(mp)
            binds[vol] = { 'bind': mp, 'mode': mode }
        # additional volumes specified by the owner
        for volume in container.volumes:
            mp = volume.mountpoint
            volumes.append(mp)
            binds[volume.volumename] = { 'bind': mp, 'mode': volume.mode(container.user) } 
        host_config = self.client.create_host_config(
            binds = binds,
            privileged = True
        )
        networking_config = { 'EndpointsConfig': { self.network: {} } }
        ports = [ 8000 ] #FIXME
        self.client.create_container(
            name = container.name,
            image = container.image.imagename,
            detach = True,
            hostname = container.name,
            host_config = host_config,
            networking_config = networking_config,
        #    command = container.command, #for notebook it is not set
            environment = container.environment,
            volumes = volumes,
            ports = ports
        )
        logger.debug("Container created")
        return self.get_container(container)

    def run_container(self, container):
        docker_container_info = self.get_container(container)
        if docker_container_info is None:
            logger.debug("Container did not exist, Creating new one")
            docker_container_info = self.create_container(container)
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
        container.is_running = False
        container.save()
        logger.debug("Container stopped %s (marked to remove %s)" % (container.name, container.mark_to_remove))
        if container.mark_to_remove:
            self.remove_container(container)

    def remove_container(self, container):
        self.client.remove_container(container.name)
        logger.debug("Container removed %s" % container.name)
        container.delete()

#FIXME: az execute2 lesz az igazi...
    def execute(self, container, command):
        logger.info("execution: %s in %s" % (command, container))
        execution = self.client.exec_create(container = container.name, cmd = shlex.split(command))
        return self.client.exec_start(execution, detach = False)

    def execute2(self, container, command):
        logger.info("execution: %s in %s" % (command, container))
        execution = self.client.exec_create(container = container.name, cmd = shlex.split(command))
        response = self.client.exec_start(exec_id = execution['Id'], stream = False)
        check = self.client.exec_inspect(exec_id = execution['Id'])
        if check['ExitCode'] != 0:
            logger.error('Execution %s in %s failed -- %s' % (command, container, check))
        return response.decode()

