import os
import json
import random
from os import path
from netaddr import IPAddress

from kooplex.lib import get_settings, mkdir_project
from kooplex.lib import Docker#, proxy_addroute, proxy_removeroute

class Spawner:

    def __init__(self, user, project, containertype, env_generator, volumemapping):
        self.user = user.user
        self.project = project
        self.containertype = containertype
        self.env_generator = env_generator
        self.volumemapping = volumemapping
        container_name_info = { 'username': user.username, 'projectname': project.name_with_owner }
        self.container_name = get_settings('spawner', 'pattern_containername') % container_name_info
        self.docker = Docker()

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
        environment_dict = self.env_generator(container)
        container.environment = json.dumps(environment_dict)
        # now we copy information from project to container instance
        container.init()

        #create folders here and set ownership
        mkdir_project(self.user, self.project)

        return container

    def start_container(self, container):
        from kooplex.lib import proxy_addroute
        self.docker.run_container(container, self.volumemapping)
##import pwgen
#        jupyter_startsession(container)
        container.is_running = True
        container.save()
        proxy_addroute(container)

    def run_container(self):
        container = self.get_container()
        if container is None:
            container = self.new_container()
        self.start_container(container)

#    def stop_session(self, session):
#        jpcli = Jupyter(session.notebook)
#        jpcli.stop_session(session)



#################################################################

def spawn_project_container(user, project):
    from kooplex.hub.models import ContainerType
    from .filesystem import G_OFFSET
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
    def env_generator(container):
        return {
            'NB_USER': user.username,
            'NB_UID': user.uid,
            'NB_GID': user.gid,
            'NB_URL': container.proxy_path,
            'NB_PORT': 8000,
            'NB_TOKEN': container.user.token,
            'PR_ID': project.id,
            'PR_NAME': project.name,
            'PR_FULLNAME': project.name,
            'PR_PWN': project.name_with_owner,
            'PR_MEMBERS': ",".join([ str(u.uid) for u in project.collaborators ]),
            'PR_URL': project.url_gitlab,
            'GID_OFFSET': G_OFFSET,
    #        'MNT_GIDS': ",".join(mpgids)  #FIXME: still missing
        }
    try:
        notebook = ContainerType.objects.get(name = 'notebook')
        spawner = Spawner(user, project, notebook, env_generator, volumemapping)
        spawner.run_container()
    except:
        raise

def stop_project_container(container):
    from kooplex.lib import proxy_removeroute
    Docker().stop_container(container)
    container.is_running = False
    container.save()
    try:
        proxy_removeroute(container)
    except KeyError:
        # if there was no proxy path saved we silently ignore the exception
        #pass
        raise #FIXME: for debug reasons we dont yet catch exception here

