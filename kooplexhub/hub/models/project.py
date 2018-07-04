import logging

from django.db import models
from django.contrib.auth.models import User
from django.template.defaulttags import register
from django.db.models.signals import post_save
from django.dispatch import receiver

from .image import Image
from .scope import ScopeType

from kooplex.settings import KOOPLEX
from kooplex.lib import standardize_str

logger = logging.getLogger(__name__)


class Project(models.Model):
    name = models.TextField(max_length = 200, null = False)
    description = models.TextField(null = True)
    image = models.ForeignKey(Image, null = True)

    def __str__(self):
        return self.name

    def __lt__(self, p):
        return self.name < p.name

    @property
    def cleanname(self):
        return standardize_str(self.name)

    @property
    def owner(self):
        return UserProjectBinding.objects.get(project = self, is_owner = True).user

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

    @property
    def course(self):
        from .course import Course
        return Course.objects.get(project = self)

    @staticmethod
    def get_userproject(project_id, user):
        return UserProjectBinding(user = user, project_id = project_id).project

#class Project(ProjectBase):
#    scope = models.ForeignKey(ScopeType, null = True)
#
#    _collaborators = None
#    @property
#    def collaborators(self):
#        if self._collaborators is None:
#            self._collaborators = UserProjectBinding.objects.filter(project = self)
#        for upb in self._collaborators:
#            yield upb.user
#
#    def is_userauthorized(self, user):
#        return True if user == self.owner or user in self.collaborators else False

class UserProjectBinding(models.Model):
    user = models.ForeignKey(User, null = False)
    project = models.ForeignKey(Project, null = False)
    is_hidden = models.BooleanField(default = False)
    is_owner = models.BooleanField(default = False)

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



#FIXME: project del signal -> container karbantart