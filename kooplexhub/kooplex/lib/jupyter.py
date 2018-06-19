import os
import requests

from kooplex.settings import KOOPLEX
from kooplex.lib import keeptrying

def jupyter_session(container):
    """
    """
    info = { 'containername': container.name }
    kw = {
        'url': os.path.join(KOOPLEX.get('spawner', {}).get('pattern_jupyterapi') % info, 'sessions'), 
        'headers': {'Authorization': 'token %s' % container.report.password, },
    }
    return keeptrying(requests.get, 50, **kw)
 
