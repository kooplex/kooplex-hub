import os.path
import json
from django.db import models

from .modelbase import ModelBase
from .project import Project
from .dashboard_server import Dashboard_server

from kooplex.lib.smartdocker import Docker
from kooplex.lib.libbase import get_settings

class Report(models.Model, ModelBase):
    id = models.IntegerField(primary_key=True)
    project_id = models.IntegerField(null=True)
    #dashboard_server = models.ForeignKey(Dashboard_server, null=True)
    name = models.CharField(max_length=200, null=True)
    file_name = models.CharField(max_length=200, null=True)
    dir_name = models.CharField(max_length=200, null=True)
    creator_name = models.CharField(max_length=200, null=True)
    path = models.CharField(max_length=200, null=True)
    url = models.CharField(max_length=200, null=True)
    cache_url = models.CharField(max_length=200, null=True)

    binds = models.TextField(null=True)
    type = models.CharField(max_length=15)

    class Meta:
        db_table = "kooplex_hub_report"

    def __init__(self, Dashboard_server, project_id, file_path, name="", type=""):
        self.file_name = os.path.split(file_name)[1]
        self.name = os.path.splitext(self.file_name)[0]
        self.type = type
        self.dashboard_server = Dashboard_server

        self.project_id = project_id
        project = Project.objects.get(id=project_id)
        self.path = os.path.join(project.home, file_path)
        self.creator_name = project.owner_username
        self.url = os.path.join(self.dashboard_server.url, self.path)
        self.cache_url = os.path.join(self.dashboard_server.cache_url, self.path)


    def get_environment(self):
        return self.load_json(self.environment)

    def set_environment(self, value):
        self.environment = self.save_json(value)

    def get_binds(self):
        return self.load_json(self.binds)

    def set_binds(self, value):
        self.binds = self.save_json(value)


    def deploy(self, other_files):
        from shutil import copyfile as cp
        from os import mkdir
        srv_dir = get_settings('users', 'srv_dir', None, '')

        if self.type=='html':
            docli = Docker()
            command = " jupyter-nbconvert --to html /%s/%s " % (self.dashboard_server, self.name)
            docli.exec_container(notebook, command, detach=False)

            file_to_deploy = self.name + ".html"
            print("dir_util.copy_tree(dir_from, D.dir_to)")
            print("dir_util.copy_tree(%s, %s)"%(dir_from, dir_to))

        elif self.type=='dashboard':

            print(other_files)
            if len(other_files) > 0:
                for file in other_files:
                    dashb.deploy_data(notebook.image.split("%s-notebook-" % prefix)[1], project, notebook_path_dir,
                                      file, extradir=ipynb_dir)

        self.dashboard_server.get_dir_to(self, username, path_with_namespace, extradir)
        dir_util.mkpath(self.dashboard_server.dir_to)
        if os.path.isdir(self.dir_from):
            print("dir_util.copy_tree(dir_from, D.dir_to)")
        else:
            try:
                print(" Err = copyfile(D.path_from, D.path_to)")
            except  IOError:
                print_debug("ERROR: file cannot be written to %s" % destination)