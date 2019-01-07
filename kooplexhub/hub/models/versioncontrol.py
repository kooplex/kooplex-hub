import logging

from django.db import models
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from .project import Project

logger = logging.getLogger(__name__)


class VCToken(models.Model):
    TP_GITHUB = 'github'
    TP_GITLAB = 'gitlab'
    TYPE_LIST = [ TP_GITHUB, TP_GITLAB ]

    user = models.ForeignKey(User, null = False)
    token = models.CharField(max_length = 256, null = False) # FIXME: dont store as clear text
    backend_type = models.CharField(max_length = 16, choices = [ (x, x) for x in TYPE_LIST ], default = TP_GITHUB)
    url = models.CharField(max_length = 128, null = True)
    last_used = models.DateTimeField(null = True)
    error_flag = models.BooleanField(default = False)       # TODO: save error message maybe stored in a separate table
    

class VCProject(models.Model):
    token = models.ForeignKey(VCToken, null = False)
    project_name = models.CharField(max_length = 512, null = False)
    last_seen = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return "Version control repository %s/%s" % (self.token.url, self.project_name)

class VCProjectProjectBinding(models.Model):
    project = models.ForeignKey(Project, null = False)
    vcproject = models.ForeignKey(VCProject, null = False)

    @staticmethod
    def getbinding(user, project):
        for b in VCProjectProjectBinding.objects.filter(project = project):
            if b.vcproject.token.user == user:
                yield b

    @property
    def otherprojects(self):
        for b in VCProjectProjectBinding.objects.filter(vcproject = self.vcproject):
            yield b.project
