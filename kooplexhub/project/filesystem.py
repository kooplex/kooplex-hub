import os
import time

from kooplexhub.settings import KOOPLEX

from hub.lib import dirname

mp_project = KOOPLEX.get('mountpoint_hub', {}).get('project', '/mnt/project')
mp_report_prepare = KOOPLEX.get('mountpoint_hub', {}).get('report_prepare', '/mnt/report_prepare')

def path_project(project):
    return os.path.join(mp_project, project.subpath)

#TODO: only if report app is loaded
def path_report_prepare(project):
    return os.path.join(mp_report_prepare, project.subpath)

def garbage_project(project):
    return os.path.join(dirname.mp_garbage, project.creator.username, "project-%s.%f.tar.gz" % (project.subpath, time.time()))
  
