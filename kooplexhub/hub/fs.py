import os
import time

from .conf import HUB_SETTINGS

def userhome(user):
    return os.path.join(
        HUB_SETTINGS["mounts"]["home"]["mountpoint_hub"],
        HUB_SETTINGS["mounts"]["home"]["folder"].format(user=user),
    )

def usergarbage(user):
    return os.path.join(
        HUB_SETTINGS["mounts"]["garbage"]["mountpoint_hub"],
        HUB_SETTINGS["mounts"]["garbage"]["folder"].format(user=user),
    )

def userscratch(user):
    return os.path.join(
        HUB_SETTINGS["mounts"]["scratch"]["mountpoint_hub"],
        HUB_SETTINGS["mounts"]["scratch"]["folder"].format(user=user),
    )

def userhome_garbage(user):
    return os.path.join(
        HUB_SETTINGS["mounts"]["garbage"]["mountpoint_hub"],
        HUB_SETTINGS["mounts"]["home"]["garbage"].format(user=user, time=timei.time()),
    )

