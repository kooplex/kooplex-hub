import os
import requests

from kooplex.lib import get_settings, keeptrying

def jupyter_session(container):
    """
    """
    info = { 'containername': container.name }
    kw = {
        'url': os.path.join(get_settings('spawner', 'pattern_jupyterapi') % info, 'sessions'), 
        'headers': {'Authorization': 'token %s' % container.report.password, },
    }
    return keeptrying(requests.get, 50, **kw)
 
