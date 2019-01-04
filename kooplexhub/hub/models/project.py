import logging

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register
from django.db.models.signals import post_save
from django.dispatch import receiver

from .image import Image
from .group import Group

from kooplex.settings import KOOPLEX
from kooplex.lib import standardize_str

logger = logging.getLogger(__name__)

SCP_LOOKUP = {
    'public': 'Authenticated users can list and may join this project.',
    'internal': 'Users in specific groups can list and may join this project.',
    'private': 'Creator can invite collaborators to this project.',
}


class Project(models.Model):
    SCP_PUBLIC = 'public'
    SCP_INTERNAL = 'internal'
    SCP_PRIVATE = 'private'
    SCOPE_LIST = [ SCP_PUBLIC, SCP_INTERNAL, SCP_PRIVATE ]

    name = models.TextField(max_length = 200, null = False)
    description = models.TextField(null = True)
    image = models.ForeignKey(Image, null = True)
    scope = models.CharField(max_length = 16, choices = [ (x, SCP_LOOKUP[x]) for x in SCOPE_LIST ], default = SCP_PRIVATE)

    def __str__(self):
        return self.name

    def __lt__(self, p):
        return self.name < p.name

    @property
    def cleanname(self):
        return standardize_str(self.name)

###    @property
###    def owner(self):  #FIXME: depracated
###        for binding in UserProjectBinding.objects.filter(project = self):
###            if binding.role == UserProjectBinding.RL_CREATOR:
###                yield binding.user

    @property
    def name_with_owner(self):
        return "%s-%s" % (standardize_str(self.name), self.owner.username)

    @property
    def safename(self):
        try:
            return self.name_with_owner
        except UserProjectBinding.DoesNotExist:
            return self.cleanname

    _volumes = None
    @property
    def volumes(self):
        from .volume import VolumeProjectBinding, Volume
        if self._volumes is None:
            self._volumes = [ binding.volume for binding in VolumeProjectBinding.objects.filter(project = self) ]
        for volume in self._volumes:
            yield volume

    @property
    def functional_volumes(self):
        from .volume import Volume
        for volume in self.volumes:
            if volume.is_volumetype(Volume.FUNCTIONAL):
                yield volume

    @property
    def storage_volumes(self):
        from .volume import Volume
        for volume in self.volumes:
            if volume.is_volumetype(Volume.STORAGE):
                yield volume

    @property
    def containers(self):
        from .container import ProjectContainerBinding
        for binding in ProjectContainerBinding.objects.filter(project = self):
            yield binding.container

    @register.filter
    def get_usercontainer(self, user):
        from .container import ProjectContainerBinding
        for binding in ProjectContainerBinding.objects.filter(project = self):
            if binding.container.user == user:
                return binding.container

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

    def is_collaborator(self, user):
        try:
            return UserProjectBinding.objects.get(project = self, user = user).role == UserProjectBinding.RL_COLLABORATOR
        except UserProjectBinding.DoesNotExist:
            return False

    @property
    def course(self):
        from .course import Course
        return Course.objects.get(project = self)

    @staticmethod
    def get_userproject(project_id, user):
        return UserProjectBinding(user = user, project_id = project_id).project

    def report_mapping4user(self, user):
        from .course import Course
        try:
            for mapping in self.course.report_mapping4user(user):
                yield mapping
        except Course.DoesNotExist:
            pass
        logger.warn("NotImplementedError")


RL_LOOKUP = {
    'creator': 'The creator of this project.',
    'administrator': 'Can modify project properties.',
    'member': 'Member of this project.',
}

class UserProjectBinding(models.Model):
    RL_CREATOR = 'creator'
    RL_ADMIN = 'administrator'
    RL_COLLABORATOR = 'member'
    ROLE_LIST = [ RL_CREATOR, RL_ADMIN, RL_COLLABORATOR ]

    user = models.ForeignKey(User, null = False)
    project = models.ForeignKey(Project, null = False)
    is_hidden = models.BooleanField(default = False)
    role = models.CharField(max_length = 16, choices = [ (x, RL_LOOKUP[x]) for x in ROLE_LIST ], null = False)

    def __str__(self):
       return "%s-%s" % (self.project.name, self.user.username)

    @staticmethod
    def setvisibility(project, user, hide):
        try:
            binding = UserProjectBinding.objects.get(user = user, project = project, is_hidden = not hide)
            binding.is_hidden = hide
            binding.save()
        except UserProjectBinding.DoesNotExist:
            raise ProjectDoesNotExist

class GroupProjectBinding(models.Model):
    group = models.ForeignKey(Group, null = False)
    project = models.ForeignKey(Project, null = False)



#FIXME: project del signal -> container karbantart
