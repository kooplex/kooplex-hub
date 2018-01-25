import logging

from django.contrib.auth.hashers import check_password

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
            if check_password(password, user.password) or password == user.password: #FIXME: for backward compatibility SHOULD BE REMOVED latter comparison
                logger.info("authenticated: %s" % user)
            else:
                logger.warning("user exists, but provided a wrong password: %s" % user)
                user = None
        except User.DoesNotExist:
            logger.info("does not exist: %s" % username)
            user = None
        return user

    def get_user(self, user_ptr):
        try:
            logger.debug("get user_ptr: %d" % user_ptr)
            return User.objects.get(user_ptr = user_ptr)
        except:
            logger.warning("unknown user_ptr: %d" % user_ptr)
            return None


