import os
import logging
import requests
import base64

from kooplex.lib import get_settings, keeptrying
from .authentication import create_user
from kooplex.hub.models import User

logger = logging.getLogger(__name__)

class AuthBackend:
    url = "https://www.ebi.ac.uk/ena/portal/ams/webin"

    def authenticate(self, **credentials):
        # Webin-44609 / lLIZDfog
        username = credentials.get('username', '')
        password = credentials.get('password', '')
        secret = username+':'+password
        kw = {
            'url': os.path.join(self.url, 'auth'),
            'headers': { 
                'Authorization': 'Basic %s' % base64.b64encode(secret.encode('utf-8')).decode('ascii'),
                'Content-Type': 'application/json'
            }
        }
        response = keeptrying(requests.post, 10, **kw)
        status_code = response.status_code
        information = response.json()
        logger.info('authenticating username: %s -> Code: %d -- %s' % (username, status_code, information))
        if status_code != 200:
            logger.warning('user %s is not authenticated' % username)
            return None
        try:
            return User.objects.get(username = username)
        except User.DoesNotExist:
            return create_user(username, first_name, last_name, email)

    def get_user(self, user_ptr):
        try:
            logger.debug("get user_ptr: %d" % user_ptr)
            return User.objects.get(user_ptr = user_ptr)
        except:
            logger.warning("unknown user_ptr: %d" % user_ptr)
            return None

