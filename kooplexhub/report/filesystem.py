import os
import time

from kooplexhub.settings import KOOPLEX

from hub.lib import dirname
from hub.lib.filesystem import _copy_dir, _rmdir   #, _grantgroupaccess
from kooplexhub.lib import bash
from project.filesystem import path_report_prepare

mp_report = dirname.MP.get('report', '/mnt/report')

def subpath(report):
    return dirname.MP.get('subPath_report', '{report.id}').format(report = report)



def dir_reportcandidate(project):
    from .models import Report #, ReportType
    # query from reporttypes the informations below
    # rts = ReportType.objects.all()
    # list_of_extensions = []
    # search_dirs = []
    # for rt in rts:
    #   list_of_extensions.extend(rts.list_of_extensions)
    list_of_extensions = ["py", "ipynb", "R", "html"]   
    #   search_dirs.extend(rts.search_dirs)
    search_dirs = ["","_build","_build/html/"] 
    dir_reportprepare = path_report_prepare(project)
    #offset = len(dir_reportprepare) + 1
    #dir_used = [ r.folder for r in Report.objects.filter(project = project) ]
    #abs_path = lambda x: os.path.join(dir_reportprepare, x)
   # leaves = []
   # for root, _, files in os.walk(dir_reportprepare):
   #     #FIXME: filter files
   #     r = root[offset:]
   #     leaves.extend(list(map(lambda x: os.path.join(r, x), files)))
   # return leaves
    pp=""
    files = []
    for sdir in  search_dirs:
        for rdir in os.listdir(dir_reportprepare):
            try:
                for rfile in filter(lambda c: c.split(".")[-1] in list_of_extensions, os.listdir(os.path.join(dir_reportprepare,rdir,sdir))):
                    files.append( os.path.join(rdir,sdir,rfile))
            except:
                continue
    return files


def publish(report):
    dir_source = os.path.join(path_report_prepare(report.project), report.folder)
    #if not os.path.exists(project_report_root):
    #    _mkdir(project_report_root, other_rx = True)
    #    n = report.mark_projectservices_restart(f"Need to mount report folder for project {report.project}")
    #    logger.info(f'{n} services marked as need to restart, due to creation of folder {project_report_root}')
    dir_target = os.path.join(mp_report, subpath(report))
    _copy_dir(dir_source, dir_target, remove = False)
    nginx_id=101
    acl = 'rXtcy' 
    bash(f'nfs4_setfacl -R -a A::{nginx_id}:{acl} {dir_target}')
    bash(f'nfs4_setfacl -R -a A::EVERYONE@:{acl} {dir_target}')
    #_grantgroupaccess(1000, dir_target)

def remove(report):
    dir_target = os.path.join(mp_report, subpath(report))
    #garbage = Filename.report_garbage(report)
    #_archivedir(dir_source, garbage, remove = True)
    _rmdir(dir_target)

