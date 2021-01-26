import os
import logging

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from .group import Group

from kooplex.settings import KOOPLEX
from kooplex.lib import standardize_str

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
        try:
            return UserProjectBinding.objects.get(project = self, role = UserProjectBinding.RL_CREATOR).user
        except UserProjectBinding.DoesNotExist:
            logger.warning(f'no creator for {self.name} {self.id}')
            return

    @property
    def cleanname(self):
        return standardize_str(self.name)

    @property
    def uniquename(self):
        return f'{self.cleanname}-{self.creator.username}' if self.creator else f'{self.cleanname}-nobody'

    #FIXME: is it used anywhere?
###OBSOLETED    @property
###OBSOLETED    def safename(self):
###OBSOLETED        try:
###OBSOLETED            return self.name_with_owner
###OBSOLETED        except UserProjectBinding.DoesNotExist:
###OBSOLETED            return self.cleanname

    @register.filter
    def get_userz_services(self, user):
        from .service import ProjectServiceBinding
        return [ binding.service for binding in ProjectServiceBinding.objects.filter(project = self, service__user = user) ]


    @register.filter
    def is_hiddenbyuser(self, user):
        try:
            return UserProjectBinding.objects.get(project = self, user = user).is_hidden
        except UserProjectBinding.DoesNotExist:
            logger.error("Binding is missing! CourseProject: %s & User: %s" % (self, user))
            return True

    def is_user_authorized(self, user):
        try:
            UserProjectBinding.objects.get(user = user, project = self)
            return True
        except UserProjectBinding.DoesNotExist:
            return False

    @register.filter
    def is_admin(self, user):
        try:
            return UserProjectBinding.objects.get(project = self, user = user).role in [ UserProjectBinding.RL_CREATOR, UserProjectBinding.RL_ADMIN ]
        except UserProjectBinding.DoesNotExist:
            return False

    @property
    def admins(self):
        return [ b.user for b in UserProjectBinding.objects.filter(project = self, role__in = [ UserProjectBinding.RL_CREATOR, UserProjectBinding.RL_ADMIN ]) ]

    def is_collaborator(self, user):
        try:
            return UserProjectBinding.objects.get(project = self, user = user).role == UserProjectBinding.RL_COLLABORATOR
        except UserProjectBinding.DoesNotExist:
            return False

    @property
    def collaborators(self):
        return [ b.user for b in UserProjectBinding.objects.filter(project = self) ]

    @property
    def userprojectbindings(self):
        return list(UserProjectBinding.objects.filter(project = self))

    @property
    def reports(self):
        from .report import Report
        return Report.objects.filter(project = self)


    @staticmethod
    def get_userproject(project_id, user):
        return UserProjectBinding.objects.get(user = user, project_id = project_id).project

    def set_roles(self, roles):
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


class UserProjectBinding(models.Model):
    RL_CREATOR = 'creator'
    RL_ADMIN = 'administrator'
    RL_COLLABORATOR = 'member'
    RL_LOOKUP = {
        RL_CREATOR: 'The creator of this project.',
        RL_ADMIN: 'Can modify project properties.',
        RL_COLLABORATOR: 'Member of this project.',
    }
    ROLE_LIST = [ RL_CREATOR, RL_ADMIN, RL_COLLABORATOR ]

    user = models.ForeignKey(User, null = False)
    project = models.ForeignKey(Project, null = False)
    is_hidden = models.BooleanField(default = False)
    role = models.CharField(max_length = 16, choices = RL_LOOKUP.items(), null = False)

    class Meta:
        unique_together = [['user', 'project']]

    def __str__(self):
       return "%s-%s" % (self.project.name, self.user.username)

    @property
    def uniquename(self):
        return "%s-%s" % (self.project.uniquename, self.user.username)

    @staticmethod
    def setvisibility(project, user, hide):
        try:
            binding = UserProjectBinding.objects.get(user = user, project = project, is_hidden = not hide)
            binding.is_hidden = hide
            binding.save()
        except UserProjectBinding.DoesNotExist:
            raise ProjectDoesNotExist


@receiver(pre_save, sender = UserProjectBinding)
def assert_single_creator(sender, instance, **kwargs):
    p = instance.project
    try:
        upb = UserProjectBinding.objects.get(project = p, role = UserProjectBinding.RL_CREATOR)
        if instance.role == UserProjectBinding.RL_CREATOR:
            assert upb.id == instance.id, "Project %s cannot have more than one creator" % p
    except UserProjectBinding.DoesNotExist:
        assert instance.role == UserProjectBinding.RL_CREATOR, "The first user project binding must be the creator %s" % instance

@receiver(post_save, sender = UserProjectBinding)
def mkdir_project(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import mkdir_project
    if instance.role == UserProjectBinding.RL_CREATOR:
        mkdir_project(instance.project)

@receiver(post_save, sender = UserProjectBinding)
def grantaccess_project(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import grantaccess_project
    if created and instance.role != UserProjectBinding.RL_CREATOR:
        grantaccess_project(instance)

@receiver(post_save, sender = UserProjectBinding)
def grantaccess_report(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import grantaccess_report
    if created:
        for report in instance.project.reports:
            grantaccess_report(report, instance.user)

@receiver(pre_delete, sender = UserProjectBinding)
def revokeaccess_project(sender, instance, **kwargs):
    from kooplex.lib.filesystem import revokeaccess_project
    revokeaccess_project(instance)

@receiver(pre_delete, sender = UserProjectBinding)
def garbagedir_project(sender, instance, **kwargs):
    from kooplex.lib.filesystem import garbagedir_project
    if instance.role == UserProjectBinding.RL_CREATOR:
        garbagedir_project(instance.project)

@receiver(post_save, sender = UserProjectBinding)
def revokeaccess_report(sender, instance, **kwargs):
    from kooplex.lib.filesystem import revokeaccess_report
    for report in instance.project.reports:
        revokeaccess_report(report, instance.user)


@receiver(pre_delete, sender = UserProjectBinding)
def assert_not_shared(sender, instance, **kwargs):
    from .service import Service, ProjectServiceBinding
    bindings = UserProjectBinding.objects.filter(project = instance.project)
    if instance.role == UserProjectBinding.RL_CREATOR:
        assert len(bindings) == 1, f'Cannot delete creator binding because {len(bindings)} project bindings exists'
    for psb in ProjectServiceBinding.objects.filter(project = instance.project, service__user = instance.user):
        if psb.service.state == Service.ST_RUNNING:
            psb.service.state = Service.ST_NEED_RESTART
            psb.service.save()
        psb.delete()
