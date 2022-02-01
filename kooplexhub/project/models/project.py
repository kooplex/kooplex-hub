import os
import logging

from django.db import models
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)


class Project(models.Model):
    SCP_PUBLIC = 'public'
    SCP_INTERNAL = 'internal'
    SCP_PRIVATE = 'private'
    SCP_LOOKUP = {
        SCP_PRIVATE: 'Creator can invite collaborators to this project.',
        SCP_INTERNAL: 'Users in specific groups can list and may join this project.',
        SCP_PUBLIC: 'Authenticated users can list and may join this project.',
    }

    name = models.TextField(max_length = 200, null = False)
    description = models.TextField(null = True)
    scope = models.CharField(max_length = 16, choices = SCP_LOOKUP.items(), default = SCP_PRIVATE)

    def __str__(self):
        return self.name

    def __lt__(self, p):
        return self.name < p.name

    @property
    def description_is_long(self):
        return len(self.description) >= 20
    @property
    def short_description(self):
        return self.description[:17] + "..." if self.description_is_long else self.description

    @property
    def creator(self):
        from .userprojectbinding import UserProjectBinding
        try:
            return UserProjectBinding.objects.get(project = self, role = UserProjectBinding.RL_CREATOR).user
        except UserProjectBinding.DoesNotExist:
            logger.warning(f'no creator for {self.name} {self.id}')
            return

    @property
    def uniquename(self):
        return f'{self.name}-{self.creator.username}' if self.creator else f'{self.name}-nobody'

    def is_user_authorized(self, user):
        from .userprojectbinding import UserProjectBinding
        try:
            UserProjectBinding.objects.get(user = user, project = self)
            return True
        except UserProjectBinding.DoesNotExist:
            return False

    def is_admin(self, user):
        from .userprojectbinding import UserProjectBinding
        try:
            return UserProjectBinding.objects.get(project = self, user = user).role in [ UserProjectBinding.RL_CREATOR, UserProjectBinding.RL_ADMIN ]
        except UserProjectBinding.DoesNotExist:
            return False

    @property
    def admins(self):
        from .userprojectbinding import UserProjectBinding
        return [ b.user for b in UserProjectBinding.objects.filter(project = self, role__in = [ UserProjectBinding.RL_CREATOR, UserProjectBinding.RL_ADMIN ]) ]

    def is_collaborator(self, user):
        from .userprojectbinding import UserProjectBinding
        try:
            return UserProjectBinding.objects.get(project = self, user = user).role == UserProjectBinding.RL_COLLABORATOR
        except UserProjectBinding.DoesNotExist:
            return False

    @property
    def collaborators(self):
        from .userprojectbinding import UserProjectBinding
        return [ b.user for b in UserProjectBinding.objects.filter(project = self) ]

    @property
    def userprojectbindings(self):
        from .userprojectbinding import UserProjectBinding
        return list(UserProjectBinding.objects.filter(project = self))

    @property
    def reports(self):
        from .report import Report
        return Report.objects.filter(project = self)


    @staticmethod
    def get_userproject(project_id, user):
        from .userprojectbinding import UserProjectBinding
        return UserProjectBinding.objects.get(user = user, project_id = project_id).project

    def set_roles(self, roles):
        from .userprojectbinding import UserProjectBinding
        msg = []
        for role in roles:
            targetrole, userid = role.split('-')
            u = User.objects.get(id = userid)
            if targetrole == 'skip':
                users = []
                try:
                    UserProjectBinding.objects.get(user = u, project = self).delete()
                    users.append(str(u))
                except UserProjectBinding.DoesNotExist:
                    pass
                if len(users):
                    msg.append("User(s) removed from the collaboration: %s" % ','.join(users))
            elif targetrole == 'collaborator':
                users = []
                try:
                    upb = UserProjectBinding.objects.get(user = u, project = self)
                    if upb.role != UserProjectBinding.RL_COLLABORATOR:
                        upb.role = UserProjectBinding.RL_COLLABORATOR
                        upb.save()
                        users.append(str(u))
                except UserProjectBinding.DoesNotExist:
                    UserProjectBinding.objects.create(user = u, project = self, role = UserProjectBinding.RL_COLLABORATOR)
                    users.append(str(u))
                if len(users):
                    msg.append("User(s) set as members of the collaboration: %s" % ','.join(users))
            elif targetrole == 'admin':
                users = []
                try:
                    upb = UserProjectBinding.objects.get(user = u, project = self)
                    if upb.role != UserProjectBinding.RL_ADMIN:
                        upb.role = UserProjectBinding.RL_ADMIN    
                        upb.save()
                        users.append(str(u))
                except UserProjectBinding.DoesNotExist:
                    UserProjectBinding.objects.create(user = u, project = self, role = UserProjectBinding.RL_ADMIN)
                    msg.append("%s is in collaboration and is an admin" % u)
                if len(users):
                    msg.append("User(s) set as administrator(s) of the collaboration: %s" % ','.join(users))
        return msg


