import os
import stat
import json
import requests
from django.conf import settings

def get_settings(block, value, override=None, default=None):
    if override:
        return override
    else:
        s = getattr(settings, block)
        if s and value in s:
            return s[value]
        else:
            return default

class LibBase:

    def __init__(self, request=None):
        self.request = request
        return None

    def join_path(a, b):
        if not b or len(b) == 0:
            url = a
        elif a[-1] != '/' and b[0] != '/':
            url = a + '/' + b
        elif a[-1] == '/' and b[0] == '/':
            url = a + b[1:]
        else:
            url = a + b
        return url

    def make_url(host='localhost', path=None, port=None, https=False):
        proto = 'https://' if https else 'http://'
        port = '' if (not port or not https and port == 80 or https and port == 443) else ':' + str(port)
        url = LibBase.join_path(proto + host + port, path)
        return url

    def clean_dir(path):        
        for root, dirs, files in os.walk(path, topdown=False):
            for name in files:
                path = os.path.join(root, name)
                LibBase.chmod(path)
                os.remove(path)
            for name in dirs:
                path = os.path.join(root, name)
                LibBase.chmod(path)
                os.rmdir(os.path.join(root, name))

    def chmod(path):
        if not os.access(path, os.W_OK):
            # Is the error an access error ?
            os.chmod(path, stat.S_IWUSR)

    def ensure_dir(dir):
        if not os.path.exists(dir):
            os.makedirs(dir)
        return dir