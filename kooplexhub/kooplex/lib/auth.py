from django.contrib.auth.models import User
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.lib.debug import *
from kooplex.hub.models.user import HubUser

class Auth(object):
    """description of class"""

    def authenticate(self, username=None, password=None):
        print_debug("")
        g = Gitlab()
        res, u = g.authenticate_user(username, password)
        if u is not None:
            try:
                user = HubUser.objects.get(username=username)
            except User.DoesNotExist:
                # Create a new user. Note that we can set password
                # to anything, because it won't be checked; the password
                # from settings.py will.
                user = HubUser(username=username, password='get from settings.py', email=u['email'])
                user.is_staff = True
                user.is_superuser = u['is_admin']
                user.gitlab_id = u['id']
                user.save()
            return user
        return None

    def get_user(self, user_id):
        print_debug("%d"%user_id)
        return User.objects.get(pk=user_id)

    def add_user(self, username, password, name, email, projects_limi=100):
        gad = GitlabAdmin()
        gad.create_user(username, password, name, email, projects_limi=projects_limi)