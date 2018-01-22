#FIXME: not used at all????

#from django.contrib.auth.models import User

#from kooplex.lib.gitlab import Gitlab
#from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.hub.models.user import User

class Auth(object):
    """description of class"""

    def authenticate(self, usernamei = None, password = None):
        return User.objects.get(username = username)

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
