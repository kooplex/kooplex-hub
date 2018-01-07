import sys, os
import getopt
import json
import string
import uuid
import random
import docker
import requests as req
from os import path
from netaddr import IPAddress
from time import sleep
from io import BytesIO
from distutils.dir_util import mkpath

from kooplex.lib.libbase import LibBase, get_settings
from django.conf import settings
Setting=settings.KOOPLEX
from kooplex.lib.restclient import RestClient
from kooplex.lib.smartdocker import Docker
from kooplex.lib.proxy import Proxy
from kooplex.lib.jupyter import Jupyter
#TODO: from kooplex.hub.models import *
from kooplex.hub.models import Container, Notebook, Session, Project, MountPointProjectBinding, HubUser, VolumeProjectBinding, Volume, UserProjectBinding

from kooplex.lib import ldap

from kooplex.lib.debug import *

class Spawner(RestClient):
       
    def __init__(self, username, project, container_name=None, image=None):
        print_debug("")
        self.username = username
        #self.project_id = project_id
        self.project = project
        self.project_owner = project.owner_username
        self.project_name = project.name
        prefix = Setting['prefix']
        self.container_name = get_settings('spawner', 'notebook_container_name', container_name, prefix+'-notebook-{$username}')
        self.image = get_settings('spawner', 'notebook_image', image, prefix + '-notebook')
        self.notebook_path = get_settings('spawner', 'notebook_proxy_path', None, '{$host_port}/notebook/{$username}/{$notebook.id}')
        self.session_path = get_settings('spawner', 'session_proxy_path', None, '/notebook/{$username}/{$notebook.id}/tree')
        self.ip_pool = get_settings('spawner', 'notebook_ip_pool', None, ['172.18.20.1', '172.18.20.255'])
        self.port = get_settings('spawner', 'notebook_port', None, 8000)

        self.srv_path = get_settings('spawner', 'srv_path', None, '/srv/' + prefix)
        self.dashboards_url = get_settings('dashboards', 'base_url','')

        self.docli = Docker()         #self.make_docker_client()
        self.pxcli = self.make_proxy_client()

    def make_docker_client(self):
        print_debug("")
        d = Docker()
        url = d.get_docker_url()
        cli = docker.client.Client(base_url=url)
        return cli

    def make_proxy_client(self):
        return Proxy()

    def pick_random_ip(self):
        print_debug("")
        network_name = get_settings('docker', 'network','')
        client = self.docli.make_docker_client()
        network_inspect = client.inspect_network(network_name)
        used_ips = [ IPAddress(network_inspect['Containers'][l]['IPv4Address'].split("/")[0]).value for l in network_inspect['Containers']]
        ip_pool = list(range(IPAddress(self.ip_pool[0]).value, IPAddress(self.ip_pool[1]).value))
        for i in used_ips:
            try:
                ip_pool.remove(i)
            except ValueError:
                1==1

        ip = IPAddress(ip_pool[random.randint(0,len(ip_pool))])

        return str(ip)


    def get_container_name(self):
        print_debug("")
        name = self.container_name
        name = name.replace('{$username}', self.username)
        name = name.replace('{$project_owner}', self.project.owner_username)
        name = name.replace('{$project_name}', self.project.name)
        # To handle spaces in names
        name = name.replace(" ", "-")
        name = name.replace("_", "-")
        return name

    def get_external_url(self, path):
        print_debug("")
        url = self.pxcli.get_external_url(path)
        return url

    def define_binds(self):
        binds = {}
        svc = 'notebook'
        notebook_path = os.path.join(self.srv_path, svc)

        # constant definitions: home (for user), oc (for user), git (for user / project), share (common / project)
        projectname = self.project.path_with_namespace.replace('/', '_')
        home_host = os.path.join(self.srv_path, 'home', self.username)
        home_container = os.path.join('/home', self.username)
# handle volumes containing user data
        prefix = Setting['prefix']
        binds['%s-home' % prefix ] = { 'bind': '/mnt/.volumes/home', 'mode': 'rw' }
        binds['%s-git' % prefix ] = { 'bind': '/mnt/.volumes/git', 'mode': 'rw' }
        binds['%s-share' % prefix ] = { 'bind': '/mnt/.volumes/share', 'mode': 'rw' }

        # dynamically added data sources
        dockerclient = self.make_docker_client()
        for mpb in MountPointProjectBinding.objects.filter(project = self.project):
            if mpb.mountpoint.type == 'local':
                binds[mpb.mountpoint.mountpoint_] = {'bind': os.path.join('/mnt', mpb.mountpoint.name), 'mode': mpb.mountpoint.accessrights_}
            elif mpb.mountpoint.type == 'nfs':
                mp = mpb.mountpoint
                volname = "%s-%s-%s" % (mp.name, mp.server_, mp.mountpoint_.replace('/', '_'))
                if not volname in [ v['Name'] for v in dockerclient.volumes()['Volumes'] ]:
                    dockerclient.create_volume(
                       name = volname, 
                       driver='local', 
                       driver_opts = { 'type': 'nfs', 'o': 'addr=%s,%s' % (mp.server_, mp.accessrights_), 'device': ':' + mp.mountpoint_ },
                       labels = {}
                    )
                binds[volname] = { 'bind': os.path.join('/mnt', mp.name), 'mode': mpb.mountpoint.accessrights_ }

        for vpb in VolumeProjectBinding.objects.filter(project = self.project):
            binds[vpb.volume.name] = { 'bind': vpb.volume.container_mountpoint_, 'mode': vpb.accessrights_ }


        return binds

    def get_notebook_path(self, id):
        print_debug("")
        path = self.notebook_path
        path = path.replace('{$username}', self.username)
        path = path.replace('{$notebook.id}', id)
        return path

    def make_notebook(self):

        def mkdir(d, uid = 0, gid = 0, mode = 0b111101000):
            mkpath(d)
            os.chown(d, uid, gid)
            os.chmod(d, mode)
#TODO: gsuid set


        print_debug("")
        id = str(uuid.uuid4())
        container_name = self.get_container_name()
        notebook_path = self.get_notebook_path(id)
        external_url = self.get_external_url(notebook_path)
        ip = self.pick_random_ip()
        binds = self.define_binds()

        notebook = Notebook(
            id=id,
            docker_host=self.docli.host,
#TODO if we use socket for docker then how should this be done???? Change model?
#            docker_port=self.docli.port,
            docker_port = 2375 if not self.docli.port else self.docli.port,
            name=container_name,
            image=self.image,
            network=self.docli.network,
            ip=ip,
            privileged=True,
            command=None,
            username=self.username,
            port=self.port,
            proxy_path=notebook_path,
            external_url=external_url,
            project_owner=self.project.owner_username,
            project_name = self.project.name,
            project_id = self.project.id,
            is_stopped=False,
            type = "user",
        )
        ldp = ldap.Ldap()
        U = ldp.get_user(self.username) 
        projectname = self.project.path_with_namespace.replace('/', '_')
        projectmembers = [m.hub_user.username for m in UserProjectBinding.objects.filter(project=self.project)]
        projectowner = self.project.owner_username

        # we have to make sure if more than one mount points share the same group id, we collapse their names
        lut_gid_gidname = {}
        for mpb in MountPointProjectBinding.objects.filter(project = self.project):
            if mpb.mountpoint.type == 'nfs' and mpb.mountpoint.host_groupid > 0:
                gid_ = mpb.mountpoint.host_groupid
                gidname_ = mpb.mountpoint.name.lower()
                if not gid_ in lut_gid_gidname:
                    lut_gid_gidname[gid_] = []
                lut_gid_gidname[gid_].append(gidname_)
        mpgids = []
        for gid_, gidnames_ in lut_gid_gidname.items():
            mpgids.append("%s:%d" % (("_".join(gidnames_))[:10], gid_))

#NOTE: offset is hardcoded here!
        G_OFFSET = 20000
        notebook.set_environment({
                'NB_USER': self.username,
                'NB_UID': U.uid,
                'NB_GID': U.gid,
                'NB_URL': notebook_path,
                'NB_PORT': self.port,
                'PR_ID': self.project.id,
                'PR_NAME': self.project.groupname_,
                'PR_FULLNAME': self.project.name,
                'PR_PWN': projectname,
                'PR_MEMBERS': ",".join(projectmembers),
                'PR_URL': "ssh://git@%s/%s.git" % (get_settings('gitlab', 'ssh_host'), self.project.path_with_namespace),
                'GID_OFFSET': G_OFFSET,
                'MNT_GIDS': ",".join(mpgids)
            })

        #create folders here and set ownership
        git_host = os.path.join(self.srv_path, '_git', self.username, projectname)
        mkdir(git_host, U.uid, G_OFFSET + self.project.id, 0b111100000)
        share_host = os.path.join(self.srv_path, '_share', projectname)
        mkdir(share_host, HubUser.objects.get(username = projectowner).uid, G_OFFSET + self.project.id, 0b111111101)

        notebook.set_binds(binds)
        # TODO: make binds read-only once config is fixed
        notebook.set_ports([self.port])

        return notebook

    def get_notebook(self):
        print_debug("")
        notebooks = Notebook.objects.filter(
            username=self.username,
            image=self.image,
            project_owner=self.project.owner_username,
            project_name=self.project.name,)
        if notebooks.count() > 0:
            # TODO: verify if container is there and proxy works
            return notebooks[0]
        else:
            return None

    def start_notebook(self, notebook):
        print_debug("")
        self.docli.ensure_container_running(notebook)
        notebook.is_stopped = False
        self.pxcli.add_route(notebook.proxy_path, notebook.ip, notebook.port)
        notebook.save()
        return notebook

    def ensure_notebook_running(self):
        print_debug("")
        notebook = self.get_notebook()
        if not notebook:
            notebook = self.make_notebook()
            notebook = self.start_notebook(notebook)
        else:
            # TODO: verify if accessible, restart if necessary
            container = self.docli.get_container(notebook)
            if not container:
                notebook.delete()
                notebook = self.make_notebook()
                notebook = self.start_notebook(notebook)
            elif container.state != 'running':
                self.docli.ensure_container_removed(container)
                notebook.delete()
                notebook = self.make_notebook()
                notebook = self.start_notebook(notebook)
        return notebook

    def stop_notebook(self, notebook):
        print_debug("")
        self.docli.ensure_container_stopped(notebook)
        notebook.is_stopped=True
        print(notebook.proxy_path)
        self.pxcli.remove_route(notebook.proxy_path)
        notebook.save()

    def delete_notebook(self, notebook):
        print_debug("")
        self.docli.ensure_container_removed(notebook)
        notebook.delete()

    def ensure_notebook_stopped(self):
        print_debug("")
        notebook = self.get_notebook()
        if notebook:
            self.stop_notebook(notebook)
        else:
            # Try to stop container if running but not in DB
            notebook = self.make_notebook()
            self.docli.ensure_container_removed(notebook)

    def get_session_path(self, notebook, session):
        print_debug("")
        path = self.session_path
        path = path.replace('{$username}', self.username)
        path = path.replace('{$notebook.id}', str(notebook.id))
        path = path.replace('{$session.notebook_path}', session.notebook_path)
        return path

    def make_session(self, notebook_path, kernel):
        print_debug("")
        session = Session(
            notebook_path=notebook_path,
            kernel_name=kernel,
        )
        return session

    def start_session(self, notebook_path, kernel, repo_name, container_name, is_forked=False, project_id=0, target_id=0):
        print_debug("")
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
        print_debug("")
        jpcli = Jupyter(session.notebook)
        jpcli.stop_session(session)

    def list_sessions(self, container):
        print_debug("")
        raise NotImplementedError


class ReportSpawner(RestClient):
    def __init__(self, project, container_name=None, image=None, report=None):
        print_debug("")
        # self.project_id = project_id
        self.project = project
        self.project_name = project.name
        prefix = Setting['prefix']
        #self.container_name = get_settings('spawner', 'notebook_container_name', container_name,
        #                                   prefix + '-notebook-{$reportname}-{$randomint}-{$author_name}')
        self.container_name = prefix + '-notebook-{$reportname}-{$randomint}-{$author_name}'
        self.image = get_settings('spawner', 'notebook_image', image, prefix + '-notebook')
        self.notebook_path = get_settings('spawner', 'notebook_proxy_path', None,
                                          '{$host_port}/notebook/{$reportname}/{$notebook.id}')
        self.session_path = get_settings('spawner', 'session_proxy_path', None,
                                         '/notebook/{$reportname}/{$notebook.id}/tree')
        self.ip_pool = get_settings('spawner', 'notebook_ip_pool', None, ['172.18.20.1', '172.18.20.255'])
        self.port = get_settings('spawner', 'notebook_port', None, 8000)

        self.srv_path = get_settings('spawner', 'srv_path', None, '/srv/' + prefix)
        if report:
            self.dashboards_url = os.path.join("/notebooks", report.file_name)# + "?dashboard"
        else:
            self.dashboards_url = ""

        self.docli = Docker()  # self.make_docker_client()
        self.pxcli = self.make_proxy_client()
        self.random_id = str(random.randint(1000000,9999999))

        self.report = report

    def make_docker_client(self):
        print_debug("")
        d = Docker()
        url = d.get_docker_url()
        cli = docker.client.Client(base_url=url)
        return cli

    def make_proxy_client(self):
        return Proxy()

    def pick_random_ip(self):
        print_debug("")
        network_name = get_settings('docker', 'network', '')
        client = self.docli.make_docker_client()
        network_inspect = client.inspect_network(network_name)
        used_ips = [IPAddress(network_inspect['Containers'][l]['IPv4Address'].split("/")[0]).value for l in
                    network_inspect['Containers']]
        ip_pool = list(range(IPAddress(self.ip_pool[0]).value, IPAddress(self.ip_pool[1]).value))
        for i in used_ips:
            try:
                ip_pool.remove(i)
            except ValueError:
                1 == 1

        ip = IPAddress(ip_pool[random.randint(0, len(ip_pool))])

        return str(ip)

    def get_container_name(self):
        print_debug("")
        name = self.container_name

        name = name.replace('{$reportname}', self.report.name)
        name = name.replace('{$randomint}', self.random_id)
        name = name.replace('{$author_name}', self.report.project.safename)

        # To handle spaces in names
        name = name.replace(" ", "-")
        name = name.replace("_", "-")
        return name

    def get_external_url(self, path):
        print_debug("")
        url = self.pxcli.get_external_url(path)
        return url

    def define_binds(self):
        binds = {}
        svc = 'notebook'
        notebook_path = os.path.join(self.srv_path, svc)
        binds[os.path.join(notebook_path, 'init')] = {'bind': '/init', 'mode': 'rw'}
        binds[os.path.join(notebook_path, 'etc/hosts')] = {'bind': '/etc/hosts', 'mode': 'ro'}
        binds[os.path.join(notebook_path, 'etc/ldap/ldap.conf')] = {'bind': '/etc/ldap/ldap.conf', 'mode': 'rw'}
        binds[os.path.join(notebook_path, 'etc/nslcd.conf')] = {'bind': '/etc/nslcd.conf', 'mode': 'rw'}
        binds[os.path.join(notebook_path, 'etc/nsswitch.conf')] = {'bind': '/etc/nsswitch.conf', 'mode': 'rw'}
        # TODO: remove hardcoding!
        binds[os.path.join(notebook_path, 'etc/jupyter_report_config.py')] = {
                'bind': '/etc/jupyter_report_config.py', 'mode': 'rw'}
        binds[self.report.target_] = {'bind': "/report", 'mode': 'rw'}
        binds[os.path.join(notebook_path, 'etc/jupyter_notebook_config.py')] = {
            'bind': '/etc/jupyter_notebook_config.py', 'mode': 'rw'}


        # dynamically added data sources
        dockerclient = self.make_docker_client()


        for vpb in VolumeProjectBinding.objects.filter(project=self.project):
            binds[vpb.volume.name] = {'bind': vpb.volume.container_mountpoint_, 'mode': vpb.accessrights_}

        return binds

    def get_notebook_path(self, id):
        print_debug("")
        path = self.notebook_path
        path = path.replace('{$username}', self.report.name)
        path = path.replace('{$notebook.id}', self.random_id)
        return path

    def make_notebook(self):

        def mkdir(d, uid=0, gid=0, mode=0b111101000):
            mkpath(d)
            os.chown(d, uid, gid)
            os.chmod(d, mode)

        # TODO: gsuid set


        print_debug("")
        id = str(uuid.uuid4())
        container_name = self.get_container_name()
        #notebook_path = os.path.join(self.get_notebook_path(id),"notebooks", self.report.file_name) + "?dashboard"
        notebook_path = self.get_notebook_path(id)
        #external_url = os.path.join(self.get_external_url(notebook_path)[:-3]+"ss", "dashboard")
        external_url = os.path.join(self.get_external_url(notebook_path), "notebooks", self.report.file_name) + "?dashboard"
        #external_url = self.get_external_url(notebook_path)
        ip = self.pick_random_ip()
        binds = self.define_binds()
        self.image = self.report.image

        notebook = Notebook(
            id=id,
            username="none",
            docker_host=self.docli.host,
            # TODO if we use socket for docker then how should this be done???? Change model?
            #            docker_port=self.docli.port,
            docker_port=2375 if not self.docli.port else self.docli.port,
            name=container_name,
            image=self.image,
            network=self.docli.network,
            ip=ip,
            privileged=True,
            command=None,
            port=self.port,
            proxy_path=notebook_path, #TODO proxy mutasson a notebook?dashboard -ra
            external_url=external_url,
            project_owner="none",
            project_name=self.report.name,
            project_id=self.report.id,
            is_stopped=False,
            type="report",
        )

                # NOTE: offset is hardcoded here!
        G_OFFSET = 20000
        notebook.set_environment({
            'NB_URL': notebook_path,
            'NB_PORT': self.port,
            'PR_ID': self.report.id,
            'PR_FULLNAME': self.report.name,
            "REPORT" : "TRUE",
            "PASSWD" : self.report.password,
        })

        # create folders here and set ownership
        notebook.set_binds(binds)
        # TODO: make binds read-only once config is fixed
        notebook.set_ports([self.port])

        return notebook

    def get_notebook(self):
        print_debug("")
        notebooks = Notebook.objects.filter(
            image=self.image,
            project_name=self.report.name,
            project_id=self.report.id, )
        if notebooks.count() > 0:
            # TODO: verify if container is there and proxy works
            return notebooks[0]
        else:
            return None

    def start_notebook(self, notebook):
        print_debug("")
        self.docli.ensure_container_running(notebook)
        notebook.is_stopped = False
        self.pxcli.add_route(notebook.proxy_path, notebook.ip, notebook.port, extratarget="")
# TODO create proxy path directly to dashboard view
        #self.pxcli.add_route(notebook.external_url, notebook.ip, notebook.port, extratarget=self.dashboards_url)
        #self.pxcli.add_route("/notebook/GGG", notebook.ip, notebook.port)#, extratarget=self.dashboards_url)
        notebook.save()
        return notebook

    def delete_notebook(self, notebook):
        print_debug("")
        self.docli.ensure_container_removed(notebook)
        notebook.delete()

    def get_session_path(self, notebook, session):
        path = self.session_path
        path = path.replace('{$reportname}', self.report.name)
        path = path.replace('{$notebook.id}', str(notebook.id))
        path = path.replace('{$session.notebook_path}', session.notebook_path)
        return path

    def make_session(self, notebook_path, kernel):
        session = Session(
            notebook_path=notebook_path,
            kernel_name=kernel,
            type="report",
        )
        return session

    def start_session(self, notebook, notebook_path, kernel, container_name, project_id=0, target_id=0):
        session = self.make_session(notebook_path, kernel)
        jpcli = Jupyter(notebook, report=True, token="")
        session = jpcli.start_session(session)
        proxy_path = self.get_session_path(notebook, session)
        session.external_url = self.get_external_url(proxy_path)
        session.is_forked = False
        session.project_id = project_id
        session.target_id = target_id
        session.repo_name = "none"
        session.type = "report"
        session.container_name = container_name
        session.save()
        return session

    def stop_session(self, session):
        print_debug("")
        jpcli = Jupyter(session.notebook)
        jpcli.stop_session(session)

    def list_sessions(self, container):
        print_debug("")
        raise NotImplementedError


