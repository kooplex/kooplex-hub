import json
import logging

from kooplex.lib import get_settings
from kooplex.lib import Docker
from kooplex.lib.filesystem import mkdir_project

logger = logging.getLogger(__name__)

class Spawner:

    def __init__(self, user, project, containertype, volumemapping):
        self.user = user.user
        self.project = project
        self.containertype = containertype
        self.volumemapping = volumemapping
        container_name_info = { 'username': user.username, 'projectname': project.name_with_owner }
        self.container_name = get_settings('spawner', 'pattern_containername') % container_name_info
        self.docker = Docker()
        logging.info("user %s, project: %s, containertype: %s" % (user, project, containertype))

    def get_container(self):
        from kooplex.hub.models import Container
        try:
            # the name of the container is unique
            return Container.objects.get(name = self.container_name)
        except Container.DoesNotExist:
            return None

    def new_container(self):
        from kooplex.hub.models import Container
        container = Container(
            name = self.container_name,
            user = self.user,
            project = self.project,
            container_type = self.containertype,
        )
        # now we copy information from project to container instance
        container.save()
        container.init()
        #create folders here and set ownership
        mkdir_project(self.user, self.project)
        return container

    def start_container(self, container):
        from kooplex.lib.proxy import addroute
        self.docker.run_container(container, self.volumemapping)
        container.is_running = True
        container.save()
        addroute(container)
        logger.info("container %s" % container)

    def run_container(self):
        container = self.get_container()
        if container is None:
            container = self.new_container()
        self.start_container(container)

#################################################################

def spawn_project_container(user, project):
    from kooplex.hub.models import ContainerType
    from kooplex.lib.filesystem import G_OFFSET
    # we have to make sure if more than one mount points share the same group id, we collapse their names
#        lut_gid_gidname = {}
#        for mpb in MountPointProjectBinding.objects.filter(project = self.project):
#            if mpb.mountpoint.type == 'nfs' and mpb.mountpoint.host_groupid > 0:
#                gid_ = mpb.mountpoint.host_groupid
#                gidname_ = mpb.mountpoint.name.lower()
#                if not gid_ in lut_gid_gidname:
#                    lut_gid_gidname[gid_] = []
#                lut_gid_gidname[gid_].append(gidname_)
#        mpgids = []
#        for gid_, gidnames_ in lut_gid_gidname.items():
#            mpgids.append("%s:%d" % (("_".join(gidnames_))[:10], gid_))
    volumemapping = [
        (get_settings('spawner', 'volume-home'), '/mnt/.volumes/home', 'rw'),
        (get_settings('spawner', 'volume-git'), '/mnt/.volumes/git', 'rw'),
        (get_settings('spawner', 'volume-share'), '/mnt/.volumes/share', 'rw'),
    ]
    try:
        notebook = ContainerType.objects.get(name = 'notebook')
        spawner = Spawner(user, project, notebook, volumemapping)
        spawner.run_container()
    except:
        raise

def stop_project_container(container):
    from kooplex.lib.proxy import removeroute
    Docker().stop_container(container)
    container.is_running = False
    container.save()
    try:
        removeroute(container)
    except KeyError:
        # if there was no proxy path saved we silently ignore the exception
        pass
