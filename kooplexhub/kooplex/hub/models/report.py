import os.path
import json
from django.db import models
from django.core.urlresolvers import reverse
from shutil import copyfile as cp
from os import mkdir
from distutils import dir_util, file_util
from time import time, strftime, localtime

from .project import Project, UserProjectBinding
from .scope import ScopeType
from .user import User

from kooplex.lib import get_settings

class ReportDoesNotExist(Exception):
    pass

class Report(models.Model):
    id = models.AutoField(primary_key = True)
    creator = models.ForeignKey(User, null = False)
    name = models.CharField(max_length = 200, null = True)
    description = models.TextField(null=True)
    ts_created = models.IntegerField(null = True)
    project = models.ForeignKey(Project, null = False)
    notebook_filename = models.CharField(max_length = 200, null = True)
    scope = models.ForeignKey(ScopeType, null = False)
    password = models.CharField(max_length = 128, null = True)  #TODO: may store encrypted

    def __str__(self):
        return "%s [%s]" % (self.filename_wo_ext, self.project.name_with_owner)

    def __lt__(self, r):
        assert isinstance(r, Report)
        return self.ts_created > r.ts_created

    @property
    def pretty_ts(self):
        return strftime("%Y %m. %d.", localtime(self.ts_created))

    @property
    def filename_wo_ext(self):
        fn_wo_ext, _ = os.path.splitext(os.path.basename(self.notebook_filename))
        return fn_wo_ext

    def is_user_allowed(self, user):
        public = ScopeType.objects.get(name = 'public')
        internal = ScopeType.objects.get(name = 'internal')
        if self.scope == public:
            return True
        if self.creator == user:
            return True
        if self.scope == internal:
            for collaborator in project.collaborators:
                if collaborator == user:
                    return True
        return False

class HtmlReport(Report):
    @property
    def displaytype(self):
        return 'Html report'

    @property
    def filename(self): #FIXME: rename it
        # as the user sees in their container
        mp_home = get_settings('volumes', 'home')
        mp_share = get_settings('volumes', 'share')
        mp_git = get_settings('volumes', 'git')
        if self.notebook_filename.startswith(mp_home):
            return '/home' + self.notebook_filename[len(mp_home):]
#        if self.notebook_filename.startswith(mp_git):
#            return '/home' + self.notebook_filename[len(mp_git):]
        else:
            raise NotImplementedError

    @property
    def filename_html(self):
        fn_wo_ext, _ = os.path.splitext(self.notebook_filename)
        return fn_wo_ext + '.html'

    @property
    def filename_report_html(self):
        return os.path.join(get_settings('volumes', 'htmlreport'), self.creator.username, self.project.name_with_owner, str(self.ts_created), self.filename_wo_ext + '.html')

class DashboardReport(Report):
    image = models.ForeignKey(ScopeType, null = False)

    @property
    def displaytype(self):
        return 'Dashboard report'

    def save(self):
        # make sure the current image is saved with the model
        self.image = self.project.image
        Report.save(self)


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


def list_user_reports(user):
    for report in HtmlReport.objects.filter(creator = user):
        yield report
    for report in DashboardReport.objects.filter(creator = user):
        yield report

def list_internal_reports(user):
    internal = ScopeType.objects.get(name = 'internal')
    for upb in UserProjectBinding.objects.filter(user = user):
        for report in HtmlReport.objects.filter(project = upb.project, scope = internal):
            if report.owner == user:
                continue
            yield report
        for report in DashboardReport.objects.filter(project = upb.project, scope = internal):
            if report.owner == user:
                continue
            yield report

def list_public_reports():
    public = ScopeType.objects.get(name = 'public')
    for report in HtmlReport.objects.filter(scope = public):
        yield report
    for report in DashboardReport.objects.filter(scope = public):
        yield report

def get_report(**kw):
    try:
        return HtmlReport.objects.get(**kw)
    except:
        pass
    try:
        return DashboardReport.objects.get(**kw)
    except:
        pass
    raise ReportDoesNotExist("Cannot find either Html not Dashboard reports")

