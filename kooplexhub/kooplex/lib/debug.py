import datetime as dt
import inspect
from django.conf import settings

def get_settings(block, value, override=None, default=None):
    if override:
        return override
    else:
        s = settings.KOOPLEX[block]
        if s and value in s:
            return s[value]
        else:
            return default


def print_debug(msg=""):
    if get_settings('debug', 'debug', None, ''):
        section = inspect.getouterframes(inspect.currentframe())[1].filename[:-3]
        subsection = inspect.getouterframes(inspect.currentframe())[1].frame.f_code.co_name
        now=dt.datetime.now()
        timestamp="[ %d.%d.%d %d:%d:%d ]"%(now.year,now.month,now.day,now.hour,now.minute,now.second)
        print("DEBUG - %s: %s - %s\t - %s"%(timestamp,section,subsection,msg))
