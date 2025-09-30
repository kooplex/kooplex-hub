import logging
import re
import os

from django.db import models
from django.template.loader import render_to_string

from kooplexhub.lib import my_alphanumeric_validator

logger = logging.getLogger(__name__)

class Volume(models.Model):
    class Scope(models.TextChoices):
        PRIVATE = 'private', 'Owner can invite collaborators to use this volume.'
        INTERNAL = 'internal', 'Users in specific groups can list and may mount this volume.'
        PUBLIC = 'public', 'Authenticated users can list and may mount this volume.'
        ATTACHMENT= 'attachment', 'Users can create, list and may mount attachments.'

    folder = models.CharField(max_length = 64, validators = [ my_alphanumeric_validator('Enter a clean volume name containing only letters and numbers.') ])
    description = models.TextField(null = True)
    claim = models.CharField(max_length = 64)
    subPath = models.CharField(max_length = 64, default = "", blank = True)
    scope = models.CharField(max_length = 16, choices = Scope.choices, default = Scope.PRIVATE)
    is_present = models.BooleanField(default = True)

    class Meta:
        unique_together = [['claim', 'folder']]

    def __str__(self):
        return "Volume /{} ({}:{})".format(self.folder, self.claim, self.subPath)

#    @property
#    def name(self):
#        return self.folder


    @property
    def owner(self):
        role = self.userbindings.model.Role
        return self.userbindings.filter(role = role.OWNER).first().user
 
    @property
    def admins(self):
        Binding = self.userbindings.model
        return {
            b.user
            for b in self.userbindings
                     .filter(role__in=[Binding.Role.OWNER, Binding.Role.ADMIN])
                     .select_related('user')
        }

    def is_admin(self, user):
        return user in self.admins

    def usercontainer_names(self, user):
        return list(
            self.containerbindings
                .filter(container__user=user)
                .values_list('container__name', flat=True)
                .distinct()
        )

    @property 
    def link_drop(self): 
        from django.urls import reverse 
        return reverse('volume:destroy', args = [self.id]) if self.id and self.scope==self.Scope.ATTACHMENT else "" 

