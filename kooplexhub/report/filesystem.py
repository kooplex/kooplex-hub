import os
import time

from kooplexhub.settings import KOOPLEX

from hub.lib import dirname
from hub.lib.filesystem import _copy_dir, _rmdir   #, _grantgroupaccess
from project.filesystem import path_report_prepare

mp_report = dirname.MP.get('report', '/mnt/report')

def subpath(report):
    return dirname.MP.get('subPath_report', '{report.root}/{report.id}').format(report = report)

def dir_reportcandidate(project):
    from .models import Report
    dir_reportprepare = path_report_prepare(project)
    dir_used = [ r.folder for r in Report.objects.filter(project = project) ]
    abs_path = lambda x: os.path.join(dir_reportprepare, x)
    not_empty_folder = lambda x: os.path.isdir(abs_path(x)) and len(os.listdir(abs_path(x))) > 0 and not x in dir_used
    return list(filter(not_empty_folder, os.listdir(dir_reportprepare)))

#def assignment_correct_dir(userassignmentbinding):
#    from education.models import UserCourseBinding
#    ucb = UserCourseBinding.objects.get(user = userassignmentbinding.user, course = userassignmentbinding.assignment.course)
#    return os.path.join(assignment_correct_root(ucb.course), userassignmentbinding.assignment.folder, userassignmentbinding.user.username)

def publish(report):
    dir_source = os.path.join(path_report_prepare(report.project), report.folder)
    #if not os.path.exists(project_report_root):
    #    _mkdir(project_report_root, other_rx = True)
    #    n = report.mark_projectservices_restart(f"Need to mount report folder for project {report.project}")
    #    logger.info(f'{n} services marked as need to restart, due to creation of folder {project_report_root}')
    dir_target = os.path.join(mp_report, subpath(report))
    _copy_dir(dir_source, dir_target, remove = False)
    nginx_id=101
    acl = 'rXtcy' if readonly else 'rwaDxtcy'
    bash(f'nfs4_setfacl -R -a A::{nginx_id}:{acl} {dir_target}')
    #_grantgroupaccess(1000, dir_target)

def remove(report):
    dir_target = os.path.join(mp_report, subpath(report))
    #garbage = Filename.report_garbage(report)
    #_archivedir(dir_source, garbage, remove = True)
    _rmdir(dir_target)

###FIXME: @sudo
###FIXME: def recreate_report(report):
###FIXME:     dir_source = os.path.join(Dirname.reportprepare(report.project), report.folder)
###FIXME:     assert os.path.exists(dir_source), f"Report folder {dir_source} does not exist."
###FIXME:     index_source = os.path.join(Dirname.reportprepare(report.project), report.folder, report.index)
###FIXME:     assert os.path.exists(index_source), f"Report index {index_source} in folder {dir_source} does not exist."
###FIXME:     dir_target = Dirname.report(report)
###FIXME:     _rmdir(dir_target)
###FIXME:     snapshot_report(report)
