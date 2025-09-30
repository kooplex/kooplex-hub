import os
import time

from .conf import PROJECT_SETTINGS
from hub.conf import HUB_SETTINGS
from report.conf import REPORT_SETTINGS

def path_project(project):
    return os.path.join(
        PROJECT_SETTINGS["mounts"]["project"]["mountpoint_hub"],
        PROJECT_SETTINGS["mounts"]["project"]["folder"].format(project=project),
    )

def path_report_prepare(project):
    return os.path.join(
        REPORT_SETTINGS["mounts"]["prepare"]["mountpoint_hub"],
        REPORT_SETTINGS["mounts"]["prepare"]["folder"].format(project=project),
    )

def garbage_project(project):
    return os.path.join(
        HUB_SETTINGS["mounts"]["garbage"]["mountpoint_hub"],
        PROJECT_SETTINGS["mounts"]["project"]["garbage"].format(project=project, time=time.time()),
    )
  
def garbage_report_prepare(project):
    return os.path.join(
        HUB_SETTINGS["mounts"]["garbage"]["mountpoint_hub"],
        REPORT_SETTINGS["mounts"]["prepare"]["garbage"].format(project=project, time=time.time()),
    )
  
