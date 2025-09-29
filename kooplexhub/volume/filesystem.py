import os
import time

from hub.lib import dirname
from hub.lib.filesystem import _mkdir, _grantaccess

from .conf import VOLUME_SETTINGS
from report.conf import REPORT_SETTINGS

mp_attachment = VOLUME_SETTINGS['mounts']['attachment']['mountpoint_hub']
mp_report_prepare = REPORT_SETTINGS['mounts']['prepare']['mountpoint_hub']

def folder_attachment(volume):
    assert volume.scope == volume.Scope.ATTACHMENT, "Only attachments are automatically created"
    return os.path.join( mp_attachment, volume.subPath )

#TODO: only if report app is loaded
def path_report_prepare(volume):
    return os.path.join(mp_report_prepare, volume.subpath)



def grantaccess_volume(volume):
    _grantaccess( volume.owner, folder )
    #FIXME: everybody read only

def garbage_attachment(volume):
    if volume.scope == volume.Scope.ATTACHMENT:
        pass
    #FIXME: NotImplemented
