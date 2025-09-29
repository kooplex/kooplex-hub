import os

from ..conf import HUB_SETTINGS

mp_home = HUB_SETTINGS["mounts"]["home"]["mountpoint_hub"]
mp_garbage = HUB_SETTINGS["mounts"]["garbage"]["mountpoint_hub"]
mp_scratch = HUB_SETTINGS["mounts"]["scratch"]["mountpoint_hub"]


def userhome(user):
    return os.path.join(mp_home, user.username)

def usergarbage(user):
    return os.path.join(mp_garbage, user.username)

def userscratch(user):
    return os.path.join(mp_scratch, user.username)

