from django.contrib.auth.models import User
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.hub.models.user import User

#FIXME:
def print_debug(*v, **w): pass

class Auth(object):
    """description of class"""

    def authenticate(self, username=None, password=None):
        print_debug("IDE jjj")
        g = Gitlab()
        res, u = g.authenticate_user(username, password)
        if u is not None:
            try:
                return User.objects.get(username = username)
            except User.DoesNotExist:
                # Authenticate user does not exist
                # Create a new user.
                user = User(
                    username = username, 
                    email = u['email'], 
                    is_superuser = u['is_admin'], 
                    gitlab_id = u['id'])
                user.save()
                return user

    def get_user(self, user_id):
        print_debug("%d" % user_id)
        try:
            # Our user model descends from django.user
            return User.objects.get(user_ptr = user_id)
        except:
            pass

    def add_user(self, username, password, name, email, projects_limi = 100):
        raise Exception("lib.auth Auth.add_user called")
        gad = GitlabAdmin()
        gad.create_user(username, password, name, email, projects_limi=projects_limi)
