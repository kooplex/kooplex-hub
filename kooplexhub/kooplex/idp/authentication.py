import os
import logging
import requests

from kooplex.lib import get_settings, keeptrying
from kooplex.hub.models import User

logger = logging.getLogger(__name__)

class AuthBackend:
    """
    https://docs.djangoproject.com/en/2.0/topics/auth/customizing/#authentication-backends
    """
    def authenticate(self, **credentials):
        username = credentials.get('username', '')
        password = credentials.get('password', '')
        try:
            user = User.objects.get(username = username)
            logger.debug("user exists: %s" % user)
            if user.password == password:
                logger.info("authenticated: %s" % user)
                return user
            # user password is mismatched
        except User.DoesNotExist:
            user = None
        kw = {
            'url': os.path.join(get_settings('gitlab', 'base_url'), 'session'),
            'params': { 'login': username, 'password': password },
        }
        response = keeptrying(requests.post, 3, **kw)
        logger.debug("response status: %d" % response.status_code)
        information = response.json()
        if not 'private_token' in information:
            logger.warning('permission denied %s' % username)
            return None
        if user is not None:
            user.password = password
            user.save()
            logger.info("authenticated and password is updated: %s" % user)
            return user
        logger.debug("create a new user based on idp[gitlab] information: %s" % username)
        first_name, last_name = information['name'].split(' ', 2)
        user = User(
            username = username,
            first_name = first_name,
            last_name = last_name,
            email = information['email'],
            is_superuser = information['is_admin'],
            gitlab_id = information['id'],
            bio = information['bio'],
        )
        user.create(skip_gitlab = True)
        user.save()
        return user

    def get_user(self, user_ptr):
        try:
            logger.debug("get user_ptr: %d" % user_ptr)
            return User.objects.get(user_ptr = user_ptr)
        except:
            logger.warning("unknown user_ptr: %d" % user_ptr)
            return None


