import os
import time

from kooplexhub.settings import KOOPLEX

from hub.lib import dirname
from hub.lib.filesystem import _mkdir, _grantaccess


mp_attachment = KOOPLEX.get('mountpoint_hub', {}).get('attachment', '/mnt/attachments')
mp_report_prepare = KOOPLEX.get('mountpoint_hub', {}).get('report_prepare', '/mnt/report_prepare')

def folder_attachment(volume):
    assert volume.scope == volume.SCP_ATTACHMENT, "Only attachments are automatically created"
    return os.path.join( mp_attachment, volume.subPath )

#TODO: only if report app is loaded
def path_report_prepare(volume):
    return os.path.join(mp_report_prepare, volume.subpath)



def grantaccess_volume(volume):
    _grantaccess( volume.owner, folder )
    #FIXME: everybody read only

def garbage_attachment(volume):
    if volume.scope == volume.SCP_ATTACHMENT:
        pass
    #FIXME: NotImplemented
