import os
import time

from kooplexhub.settings import KOOPLEX

from hub.lib import dirname

mp_volume = KOOPLEX.get('mountpoint_hub', {}).get('volume', '/mnt/volume')
mp_report_prepare = KOOPLEX.get('mountpoint_hub', {}).get('report_prepare', '/mnt/report_prepare')

def path_volume(volume):
    return os.path.join(mp_volume, volume.subpath)

#TODO: only if report app is loaded
def path_report_prepare(volume):
    return os.path.join(mp_report_prepare, volume.subpath)

def garbage_volume(volume):
    return os.path.join(dirname.mp_garbage, volume.creator.username, "volume-%s.%f.tar.gz" % (volume.subpath, time.time()))


