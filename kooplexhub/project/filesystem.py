import os
import time

from .conf import PROJECT_SETTINGS
from report.conf import REPORT_SETTINGS

from hub.lib import dirname

mp_project = PROJECT_SETTINGS["mounts"]["project"]["mountpoint_hub"]
mp_report_prepare = REPORT_SETTINGS["mounts"]['prepare']['mountpoint_hub']

def path_project(project):
    return os.path.join(mp_project, project.subpath)

#TODO: only if report app is loaded
def path_report_prepare(project):
    return os.path.join(mp_report_prepare, project.subpath)

def garbage_project(project):
    return os.path.join(dirname.mp_garbage, project.creator.username, "project-%s.%f.tar.gz" % (project.subpath, time.time()))
  
def garbage_report_prepare(project):
    return os.path.join(dirname.mp_garbage, project.creator.username, "projectreport-%s.%f.tar.gz" % (project.subpath, time.time()))
  
