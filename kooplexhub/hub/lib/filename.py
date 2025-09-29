import os
import time

from ..lib import dirname

def userhome_garbage(user):
    return os.path.join(dirname.mp_garbage, "user-%s.%f.tar.gz" % (user.username, time.time()))

