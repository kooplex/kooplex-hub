import os.path
import json
from django.db import models
from django.core.urlresolvers import reverse
from shutil import copyfile as cp
from os import mkdir
from distutils import dir_util, file_util
from time import time, strftime, localtime

from .project import Project
from .container import Container

from .user import HubUser

from kooplex.lib.smartdocker import Docker
from kooplex.lib.libbase import get_settings

class Report(models.Model):
    id = models.AutoField(primary_key = True)
    creator = models.ForeignKey(HubUser, null = False)
    name = models.CharField(max_length = 200, null = True)
    description = models.TextField(null=True)
    report_type = models.ForeignKey(ReportType, null = False)
    ts_created = models.IntegerField(null = True)
    project = models.ForeignKey(Project, null = False)
    container = models.ForeignKey(Container, null = False)
    path = models.CharField(max_length = 200, null = True)
    scope = models.ForeignKey(ReportScope, null = False)
    password = models.CharField(max_length = 128, null = True)  #TODO: may store encrypted

##    wd = '_report'

    class Meta:
        db_table = "kooplex_hub_report"

##    def init(self, dashboard_server, project, creator, description, file="", type="", password=""):
##        self.ts_created = int(time())
##        self.path, self.file_name = os.path.split(file)
##        self.name = os.path.splitext(self.file_name)[0]
##        self.type = type
##        self.dashboard_server = dashboard_server
##        self.project = project
##        self.creator = creator
##        self.creator_name = self.project.owner_username
##        self.description = description
##        self.image = project.image
##        self.password = password
##
##    def __lt__(self, r):
##        assert isinstance(r, Report)
##        return self.ts_created > r.ts_created
##
##    @property
##    def ts_(self):
##        return strftime("%Y%m%d_%H%M%S", localtime(self.ts_created))
##
##    @property
##    def prettyts_(self):
##        return strftime("%Y %m. %d.", localtime(self.ts_created))
##
##
##    @property
##    def url_(self):
##        if self.type == 'html':
##            return reverse('report-open') + "?report_id=%d" %  (self.id)
##        elif self.type == 'dashboard':
###FIXME: why dashboard here
##            return os.path.join(self.dashboard_server.url, self.path, 'dashboards', self.project.home, self.ts_, self.name)
##        else:
##            assert False, "Unhandled type %s" % self.type
##
##    @property
##    def cache_url_(self):
##        assert self.type == 'html', "Unhandled type %s" % self.type
##        return os.path.join(self.dashboard_server.cache_url, self.path)
##
##    @property
##    def target_(self):
##        if self.type == 'html':
##            return os.path.join(srv_dir, self.wd, 'html', self.project.home, self.ts_)
##        elif self.type == 'dashboard':
##            return os.path.join(srv_dir, self.wd, self.dashboard_server.type, self.project.home, self.ts_)
##
##    @property
##    def entry_(self):
##        return os.path.join(self.target_, self.file_name)
##
##    @property
##    def gitdir_(self):
##        return self.project.gitdir(self.creator.username)
##
##    def get_environment(self):
##        return self.load_json(self.environment)
##
##    def set_environment(self, value):
##        self.environment = self.save_json(value)
##
##    def get_binds(self):
##        return self.load_json(self.binds)
##
##    def set_binds(self, value):
##        self.binds = self.save_json(value)
##
##    def convert_to_html(self, notebook):
##        docli = Docker()
##        nb = os.path.join('home', self.creator.username, 'git', self.path, self.name)
##        command = " jupyter-nbconvert --to html /%s.ipynb " % nb
##        docli.exec_container(notebook, command, detach=False)
##
##
##    def deploy(self, other_files):
##        if self.type=='html':
##            notebook = Notebook.objects.get(project_id = self.project.id, username = self.creator.username)
##            self.convert_to_html(notebook)
##            dir_util.mkpath(self.target_)
##            self.file_name = os.path.splitext(self.file_name)[0] + ".html"
##            file_to_deploy = os.path.join(self.gitdir_, self.path, self.file_name)
##            file_to_create = os.path.join(self.target_, self.file_name)
##            try:
##                file_util.move_file(file_to_deploy, file_to_create)
##            except:
##                os.remove(file_to_deploy)
##                raise
##
##        elif self.type=='dashboard':
##            #THIS WILL REPLACE THE FILE OPENER FUNCTION , WHICH WILL COPY THE FILES TO THE RIGHT PLACE
##            def func_replace():
##                import json
##
###                def findcell(obj, sstr):
###                    cells = obj['cells']
###                    for icell in range(len(cells)):
###                        for i in range(len(cells[icell]['source'])):
###                            if cells[icell]['source'][i].find('import') > -1 and cells[icell]['source'][i].find(
###                                    sstr) > -1:
###                                return icell, i
##
##
##            ooops = []
##            other_files.append(os.path.join(self.path, self.file_name))
##            for file in other_files:
##                file_to_deploy = os.path.join(self.gitdir_, self.path, file)
##                file_to_create = os.path.join(self.target_, file)
##                dir_util.mkpath(os.path.split(file_to_create)[0])
##                try:
##                    file_util.copy_file(file_to_deploy, file_to_create)
##                except:
##                    ooops.append(file)
##                    
##            newcell = {
##   "cell_type": "code",
##   "execution_count": 1,
##   "metadata": {
##    "collapsed": True
##   },
##   "outputs": [],
##   "source": ["import os\n","os.chdir('%s')"%os.path.join("/home/",self.project.home, self.ts_)]
##  }
##            with open(os.path.join(self.gitdir_, self.path, self.file_name),'r') as Foriginal:
##               ipynb=json.load(Foriginal)
##            ipynb['cells'].insert(0,newcell)
##
##            with open(os.path.join(self.target_, self.file_name),'w') as WW:
##               json.dump(ipynb,WW)
##
##                    
##            if len(ooops):
##                raise Exception("Error copying files: %s" % ",".join(ooops))
##
##    def remove(self):
##        dir_util.remove_tree(self.target_)
##        self.delete()


class ReportType(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)

class ScopeType(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)



def init_model():
    reporttypes = [ 'html', 'dashboard', 'dashboardserver' ]
    for rt in reporttype:
        rti = ReportType.objects.get(name = rt)
        if rti is None:
            rti = ReportType(name = rt)
            rti.save()
    scopetypes = [ 'private', 'internal', 'public' ]
    for st in scopetype:
        sti = ScopeType.objects.get(name = st)
        if sti is None:
            sti = ReportType(name = rt)
            sti.save()
