from django.contrib.auth.models import User
from kooplex.lib.gitlab import Gitlab

class Auth(object):
    """description of class"""

    def authenticate(self, username=None, password=None):
        g = Gitlab()
        res, u = g.authenticate_user(username, password)
        if u is not None:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                # Create a new user. Note that we can set password
                # to anything, because it won't be checked; the password
                # from settings.py will.
                user = User(username=username, password='get from settings.py', email=u['email'])
                user.is_staff = True
                user.is_superuser = u['is_admin']
                user.save()
            return user
        return None

    def get_user(self, user_id):
        return User.objects.get(pk=user_id)