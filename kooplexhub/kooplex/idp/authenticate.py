import os
import logging
import requests

from kooplex.lib import get_settings, keeptrying
from kooplex.hub.models import User

logger = logging.getLogger(__name__)

def gitlab_authenticate(username, password):
    kw = {
        'url': os.path.join(get_settings('gitlab', 'base_url'), 'session'),
        'params': { 'login': username, 'password': password },
    }
    response = keeptrying(requests.post, 3, **kw)
    logger.debug("response status: %d" % response.status_code)
    assert response.status_code == 201, response.json()
    information = response.json()
    details = {
        'username': username,
        'email': information['email'],
        'is_superuser': information['is_admin'],
        'gitlab_id': information['id'],
    }
    return 'private_token' in information, details

def authenticate(username, password):
    try:
        User.objects.get(username = username, password = password)
        return True, None
    except User.DoesNotExist:
        pass
    return gitlab_authenticate(username, password)

