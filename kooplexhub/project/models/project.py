import logging

from django.db import models
from django.template.defaulttags import register
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)

class Project(models.Model):
    class Scope(models.TextChoices):
        PUBLIC = 'public', 'Any authenticated user can list and may join this project.'
        INTERNAL = 'internal', 'Only users in specific groups can list and may join this project.'
        PRIVATE = 'private', 'Only the creator can invite collaborators to this project.'

    name = models.TextField(max_length = 200)
    description = models.TextField(null = True)
    scope = models.CharField(max_length = 16, choices = Scope.choices, default = Scope.PRIVATE)
    subpath = models.CharField(max_length = 200, null = True, unique = True)
    preferred_image = models.ForeignKey('container.Image', on_delete = models.CASCADE, default = None, null = True)

    def __str__(self):
        return self.name 

    def __lt__(self, p):
        return self.name < p.name

    @property
    def creator(self):
        role = self.userbindings.model.Role
        return self.userbindings.filter(role = role.CREATOR).first().user

    @property
    def admins(self):
        Binding = self.userbindings.model
        return {
            b.user
            for b in self.userbindings
                     .filter(role__in=[Binding.Role.CREATOR, Binding.Role.ADMIN])
                     .select_related('user')
        } if self.pk else {}

    def is_admin(self, user):
        return user in self.admins

    def collaborators_excluding(self, user):
        return self.userbindings.exclude(user__pk=user.pk) if self.pk else {}

    @property
    def volumes(self):
        return {
            b.volume
            for b in self.volumebindings
                     .select_related('volume')
        } if self.pk else {}

