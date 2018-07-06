"""
@author: Jozsef Steger, David Visontai
@summary: docker API driver
"""
import logging
import re
import os
import json
import shlex
from docker.client import Client

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Docker:
    dockerconf = KOOPLEX.get('docker', {})

    def __init__(self):
        base_url = self.dockerconf.get('base_url', '')
        self.client = Client(base_url = base_url)
        logger.debug("Client init")
        self.check = None

    def list_imagenames(self):
        logger.debug("Listing image names")
        pattern_imagenamefilter = KOOPLEX.get('docker', {}).get('pattern_imagename_filter', r'^image-%(\w+):\w$')
        for image in self.client.images(all = True):
            if image['RepoTags'] is None:
                continue
            for tag in image['RepoTags']:
                if re.match(pattern_imagenamefilter, tag):
                    _, imagename, _ = re.split(pattern_imagenamefilter, tag)
                    logger.debug("Found image: %s" % imagename)
                    yield imagename

    def list_volumenames(self):
        logger.debug("Listing volume names")
        volumes = self.client.volumes()
        for volume in volumes['Volumes']:
            yield volume['Name']

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
        for volume in container.volumes:
            logger.debug("container %s, volume %s" % (container, volume))
            mp = volume.mountpoint
            volumes.append(mp)
            binds[volume.name] = { 'bind': mp, 'mode': volume.mode(container.user) }
        logger.debug("container %s binds %s" % (container, binds))
        host_config = self.client.create_host_config(
            binds = binds,
            privileged = True
        )
        network = self.dockerconf.get('network', 'host')
        networking_config = { 'EndpointsConfig': { network: {} } }
        ports = self.dockerconf.get('container_ports', [ 8000 ])
        imagename = container.image.imagename if container.image else self.dockerconf.get('default_image', 'basic')
        args = {
            'name': container.name,
            'image': imagename,
            'detach': True,
            'hostname': container.name,
            'host_config': host_config,
            'networking_config': networking_config,
            'environment': container.environment,
            'volumes': volumes,
            'ports': ports,
        }
        self.client.create_container(**args)
        logger.debug("Container created")
        mapper = self.construct_mapper(container)
        self.copy_mapper(container, mapper)
        #FIXME: reportdir mapper
        return self.get_container(container)

    def construct_mapper(self, container):
        from hub.models import Volume
        user = container.user
        mapper = []
        for binding in container.volumecontainerbindings:
            if binding.volume.is_volumetype(Volume.WORKDIR):
                mapper.append('workdir:%s' % os.path.join(binding.volume.mountpoint, user.username, binding.project.name_with_owner))
            elif binding.volume.is_volumetype(Volume.SHARE):
                mapper.append('share:%s' % os.path.join(binding.volume.mountpoint, binding.project.name_with_owner))
            elif binding.volume.is_volumetype(Volume.COURSE_SHARE):
                course = binding.project.course
                if user.profile.is_courseteacher(course):
                    mapper.append('share:%s' % os.path.join(binding.volume.mountpoint, course.safecourseid))
                else:
                    mapper.append('share:%s' % os.path.join(binding.volume.mountpoint, course.safecourseid, 'public'))
            elif binding.volume.is_volumetype(Volume.COURSE_WORKDIR):
                course = binding.project.course
                if user.profile.is_courseteacher(course):
                    mapper.append('workdir:%s' % os.path.join(binding.volume.mountpoint, course.safecourseid))
                else:
                    flags = list(course.list_userflags(user))
                    if len(flags) != 1:
                        logger.error("Student %s has more course %s flags (%s) than expected" (user, course, list(flags)))
                    mapper.append('workdir:%s' % os.path.join(binding.volume.mountpoint, course.safecourseid, flags[0], user.username))
        logger.debug("container %s mapper %s" % (container, "+".join(mapper)))
        return mapper

    def copy_mapper(self, container, mapper, filename = 'mount.conf'):  #FIXME: no default here and rename method
        import tarfile
        import time
        from io import BytesIO

        tarstream = BytesIO()
        tar = tarfile.TarFile(fileobj = tarstream, mode = 'w')
        file_data = "\n".join(mapper).encode('utf8')
        tarinfo = tarfile.TarInfo(name = filename)
        tarinfo.size = len(file_data)
        tarinfo.mtime = time.time()
        tar.addfile(tarinfo, BytesIO(file_data))
        tar.close()
        tarstream.seek(0)
        try:
            status = self.client.put_archive(container = container.name, path = '/tmp', data = tarstream)
            logger.info("container %s put_archive returns %s" % (container, status))
        except Exception as e:
            logger.error("container %s put_archive fails -- %s" % (container, e))

    def reportmount(self, container, configline):
        self.copy_mapper(container, [ configline ], 'mount_report.conf')

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
        try:
            self.client.stop(container.name)
        except Exception as e:
            logger.warn("docker container not found by API -- %s" % e)
        container.is_running = False
        container.save()

    def remove_container(self, container):
        try:
            self.client.remove_container(container.name)
        except Exception as e:
            logger.warn("docker container not found by API -- %s" % e)
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
        self.check = check
        if check['ExitCode'] != 0:
            logger.error('Execution %s in %s failed -- %s' % (command, container, check))
        return response.decode()

