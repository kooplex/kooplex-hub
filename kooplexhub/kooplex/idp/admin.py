import logging

from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password


logger = logging.getLogger(__name__)

class AuthBackend:
    def authenticate(self, **credentials):
        username = credentials.get('username', '')
        password = credentials.get('password', '')
        try:
            user = User.objects.get(username = username, is_staff = True)
            if check_password(password, user.password):
                logger.debug("user authenticated: %s" % user)
            else:
                logger.debug("password mismatch: %s" % user)
                user = None
        except User.DoesNotExist:
            logger.info("user not authenticated: %s" % username)
            user = None
        return user

    def get_user(self, user_ptr):
        try:
            logger.debug("get user_ptr: %d" % user_ptr)
            return User.objects.get(id = user_ptr)
        except:
            logger.warning("unknown user_ptr: %d" % user_ptr)
            return None


