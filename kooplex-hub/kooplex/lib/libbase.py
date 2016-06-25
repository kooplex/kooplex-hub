import json
import requests
from django.conf import settings
from threadlocals.threadlocals import get_current_request

def get_settings(block, value, override, default=None):
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
    
    def get_session_store(self):
        if self.request is not None:
            return self.request.session
        else:
            request = get_current_request()
            return request.session