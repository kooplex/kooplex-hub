import logging

from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

class AuthBackend:
    def authenticate(self, **credentials):
        username = credentials.get('username', '')
        password = credentials.get('password', '')
        try:
            user = User.objects.get(username = username, password = password, is_staff = True)
            logger.debug("user authenticated: %s" % user)
        except User.DoesNotExist:
            logger.info("user not authenticated: %s" % username)
            user = None
        return user

    def get_user(self, user_ptr):
        try:
            logger.debug("get user_ptr: %d" % user_ptr)
            return User.objects.get(user_ptr = user_ptr)
        except:
            logger.warning("unknown user_ptr: %d" % user_ptr)
            return None


