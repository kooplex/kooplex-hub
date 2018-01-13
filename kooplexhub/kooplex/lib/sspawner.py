import os
import json
import random
from os import path
from netaddr import IPAddress

from kooplex.lib import get_settings, mkdir_project
from kooplex.lib import Proxy, Docker

##################
# FIXME: this class needs a major revision

class Spawner:
       
    def __init__(self, user, project, containertype, environment, volumemapping):
        self.user = user.user
        self.project = project
        self.containertype = containertype
        self.environment = environment
        self.volumemapping = volumemapping

        container_name_info = { 'username': user.username, 'projectname': project.name_with_owner }
        self.container_name = get_settings('spawner', 'pattern_containername') % container_name_info

        self.notebook_path = get_settings('spawner', 'notebook_proxy_path', None, '{$host_port}/notebook/{$username}/{$notebook.id}')
        self.session_path = get_settings('spawner', 'session_proxy_path', None, '/notebook/{$username}/{$notebook.id}/tree')

        self.ip_pool = get_settings('spawner', 'notebook_ip_pool', None, ['172.18.20.1', '172.18.20.255'])
        self.port = get_settings('spawner', 'notebook_port', None, 8000)
        self.dashboards_url = get_settings('dashboards', 'base_url','')

        self.docker = Docker()
        self.proxy = Proxy()

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
            environment = json.dumps(self.environment),
        )
        # now we copy information from project to container instance
        container.init()

        #create folders here and set ownership
        mkdir_project(self.user, self.project)

        return container

    def start_container(self, container):
        self.docker.run_container(container, self.volumemapping)
        container.is_running = True
        container.save()
        self.proxy.add_route(container.proxy_path, container.ip, 8000) #FIXME: get them

    def run_container(self):
        container = self.get_container()
        if container is None:
            container = self.new_container()
        self.start_container(container)










    def get_external_url(self, path):
        url = self.pxcli.get_external_url(path)
        return url

    def get_notebook_path(self, id):
        path = self.notebook_path
        path = path.replace('{$username}', self.user.username)
        path = path.replace('{$notebook.id}', id)
        return path

    def get_session_path(self, notebook, session):
        path = self.session_path
        path = path.replace('{$username}', self.username)
        path = path.replace('{$notebook.id}', str(notebook.id))
        path = path.replace('{$session.notebook_path}', session.notebook_path)
        return path

    def start_session(self, notebook_path, kernel, repo_name, container_name, is_forked=False, project_id=0, target_id=0):
        notebook = self.ensure_notebook_running()
        session = self.make_session(notebook_path, kernel)
        jpcli = Jupyter(notebook)#, token="aiSiga1aiFai2AiZu1veeWein5gijei8yeLay2Iecae3ahkiekeisheegh2ahgee")
        session = jpcli.start_session(session)
        proxy_path = self.get_session_path(notebook, session)
        session.external_url = self.get_external_url(proxy_path)
        session.is_forked = is_forked
        session.project_id = project_id
        session.target_id = target_id
        session.repo_name = repo_name
        session.container_name = container_name
        session.save()
        return session

    def stop_session(self, session):
        jpcli = Jupyter(session.notebook)
        jpcli.stop_session(session)



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
        ('kooplex-home', '/mnt/.volumes/home', 'rw'),
        ('kooplex-git', '/mnt/.volumes/git', 'rw'),
        ('kooplex-share', '/mnt/.volumes/share', 'rw'),
    ]
    environment = {
        'NB_USER': user.username,
        'NB_UID': user.uid,
        'NB_GID': user.gid,
#        'NB_URL': notebook_path, #FIXME
        'NB_PORT': 8000,
        'PR_ID': project.id,
        'PR_NAME': project.name, #FIXME:
        'PR_FULLNAME': project.name,
        'PR_PWN': project.name,
#        'PR_MEMBERS': ",".join(projectmembers),
#        'PR_URL': "ssh://git@%s/%s.git" % (get_settings('gitlab', 'ssh_host'), self.project.path_with_namespace),
        'GID_OFFSET': G_OFFSET,
#        'MNT_GIDS': ",".join(mpgids)
    }
    try:
        notebook = ContainerType.objects.get(name = 'notebook')
        spawner = Spawner(user, project, notebook, environment, volumemapping)
        spawner.run_container()
    except:
        raise

def stop_project_container(container):
    Docker().stop_container(container)
    container.is_running = False
    container.save()
    try:
        Proxy().remove_route(container.proxy_path)
    except KeyError:
        # if there was no proxy path saved we silently ignore the exception
        pass

