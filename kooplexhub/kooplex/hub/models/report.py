import os.path
import json
from django.db import models

from .modelbase import ModelBase
from .project import Project
from .notebook import Notebook
from .dashboard_server import Dashboard_server

from kooplex.lib.smartdocker import Docker
from kooplex.lib.libbase import get_settings

class Report(models.Model, ModelBase):
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, null=True)
    dashboard_server = models.ForeignKey(Dashboard_server, null=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=200, null=True)
    file_name = models.CharField(max_length=200, null=True)
    creator_name = models.CharField(max_length=200, null=True)
    path = models.CharField(max_length=200, null=True)
    url = models.CharField(max_length=200, null=True)
    cache_url = models.CharField(max_length=200, null=True)
    scope = models.CharField(max_length = 16, null = True)

    binds = models.TextField(null=True)
    type = models.CharField(max_length=15)

    class Meta:
        db_table = "kooplex_hub_report"

    def init(self, Dashboard_server, project, file="", type=""):
        self.path, self.file_name = os.path.split(file)
        self.name = os.path.splitext(self.file_name)[0]
        self.type = type
        self.dashboard_server = Dashboard_server

        self.project = project
        self.creator_name = self.project.owner_username
        if type == 'html':
            self.url = "/hub/worksheetsopen?project_id=%d&file=%s.html" %  (project.id, self.name)
            self.cache_url = 'na'
        elif type == 'dashboard':
            self.url = os.path.join(self.dashboard_server.url, self.path)
            self.cache_url = os.path.join(self.dashboard_server.cache_url, self.path)
        else:
            NotImplementedError("Unknown type %s" % type)

    def get_full_from_path(self, file=""):
        if file:
            return os.path.join(self.project.get_full_home(), file)
        else:
            return os.path.join(self.project.get_full_home(), self.path, self.file_name)

    def get_full_to_path(self, file=""):
        if file:
            return os.path.join(self.dashboard_server.get_full_dir_to(), self.project.home, file)
        else:
            return os.path.join(self.dashboard_server.get_full_dir_to(), self.project.home, self.path, self.file_name)

#FIXME: this is ugly
    def get_url(self):
        return os.path.join(self.dashboard_server.url, self.dashboard_server.dir, self.project.home, self.name).replace('//', '/')

    def get_cache_url(self):
        return os.path.join(self.dashboard_server.cache_url, self.project.get_relative_home(), self.name).replace('//', '/')

    def get_environment(self):
        return self.load_json(self.environment)

    def set_environment(self, value):
        self.environment = self.save_json(value)

    def get_binds(self):
        return self.load_json(self.binds)

    def set_binds(self, value):
        self.binds = self.save_json(value)


    def convert_to_html(self, notebook):
        docli = Docker()
        #OBSOLETE
        #command = " jupyter-nbconvert --to html /%s " % (os.path.join(self.project.get_relative_home(), self.path, self.name))
        nb = os.path.join('home', self.project.owner_name, 'git', self.path, self.name)
        command = " jupyter-nbconvert --to html /%s.ipynb " % nb
        docli.exec_container(notebook, command, detach=False)


    def deploy(self, other_files):
        from shutil import copyfile as cp
        from os import mkdir
        from distutils import dir_util, file_util
        srv_dir = get_settings('users', 'srv_dir', None, '')


        if self.type=='html':
            notebook = Notebook.objects.get(project_id=self.project.id, username=self.project.owner_username)
            self.convert_to_html(notebook)
            self.file_name = os.path.splitext(self.file_name)[0] + ".html"
#FIXME:
            #OBSOLETE
            #file_to_deploy = self.get_full_from_path()
            file_to_deploy = os.path.join(get_settings('users', 'srv_dir', None, ''), '_git', self.project.owner_name, self.project.path_with_namespace.replace('/', '_'), self.path, self.file_name)
            file_to_create = self.get_full_to_path()
            dir_util.mkpath(os.path.dirname(file_to_create))
            if os.path.exists(file_to_create):
                os.unlink(file_to_create)
            try:
                file_util.move_file(file_to_deploy, file_to_create)
            except:
                os.remove(file_to_deploy)
                raise

        elif self.type=='dashboard':
            other_files.append(os.path.join(self.path, self.file_name))
            for file in other_files:
                #OBSOLETE
                #file_to_deploy = self.get_full_from_path(file)
                file_to_deploy = os.path.join(get_settings('users', 'srv_dir', None, ''), '_git', self.project.owner_name, self.project.path_with_namespace.replace('/', '_'), self.path, file)
                file_to_create = self.get_full_to_path(file)
                dir_util.mkpath(os.path.split(file_to_create)[0])
                try:
                    file_util.copy_file(file_to_deploy, file_to_create)
                except:
                    1 == 1

        if os.path.isdir(self.path):
            #dir_util.copy_tree(dir_from, D.dir)
            1==1
        else:
            try:
                print(" Err = copyfile(D.path_from, D.path_to)")
            except  IOError:
                print_debug("ERROR: file cannot be written to %s" % destination)
