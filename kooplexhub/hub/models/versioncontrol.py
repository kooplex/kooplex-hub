import logging
import re

from django.db import models
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from kooplex.lib import standardize_str

from .project import Project

logger = logging.getLogger(__name__)


class VCToken(models.Model):
    TP_GITHUB = 'github'
    TP_GITLAB = 'gitlab'
    TYPE_LIST = [ TP_GITHUB, TP_GITLAB ]

    user = models.ForeignKey(User, null = False)
    token = models.CharField(max_length = 256, null = False) # FIXME: dont store as clear text
    fn_rsa = models.CharField(max_length = 256, null = False)
    backend_type = models.CharField(max_length = 16, choices = [ (x, x) for x in TYPE_LIST ], default = TP_GITHUB)
    url = models.CharField(max_length = 128, null = True)
    last_used = models.DateTimeField(null = True)
    error_flag = models.BooleanField(default = False)       # TODO: save error message maybe stored in a separate table

    @property
    def domain(self):
        return re.split(r'https?://([^/]+)', self.url)[1]


class VCProject(models.Model):
    token = models.ForeignKey(VCToken, null = False)
    project_name = models.CharField(max_length = 512, null = False)
    last_seen = models.DateTimeField(auto_now_add = True)

    def __str__(self):
        return "Version control repository %s/%s" % (self.token.url, self.project_name)

    @property
    def repository(self):
        return '{}/{}'.format(self.token.url, self.project_name)

    @property
    def cleanname(self):
        return standardize_str(self.project_name)

    @property
    def uniquename(self):
        t = self.token
        return "%s-%s-%s-%s" % (t.backend_type, t.domain, t.user.username, self.cleanname)

    @property
    def vcprojectprojectbindings(self):
        for vcpb in VCProjectProjectBinding.objects.filter(vcproject = self):
            yield vcpb

    @staticmethod
    def f_user(user):
        for vcp in VCProject.objects.all():
            if vcp.token.user == user:
                yield vcp

    @staticmethod
    def f_user_namelike(user, l):
        for vcp in VCProject.objects.filter(models.Q(project_name__icontains = l)):
            if vcp.token.user == user:
                yield vcp

    
class VCProjectProjectBinding(models.Model):
    project = models.ForeignKey(Project, null = False)
    vcproject = models.ForeignKey(VCProject, null = False)

#FIXME: deprecated
    @property
    def uniquename(self):
        vcp = self.vcproject
        t = vcp.token
        return "%s-%s-%s-%s" % (t.backend_type, t.domain, t.user.username, vcp.cleanname)

    @staticmethod
    def getbinding(user, project):
        for b in VCProjectProjectBinding.objects.filter(project = project):
            if b.vcproject.token.user == user:
                yield b

    @property
    def otherprojects(self):
        for b in VCProjectProjectBinding.objects.filter(vcproject = self.vcproject):
            yield b.project


@receiver(post_save, sender = VCProjectProjectBinding)
def mkdir_vcpcache(sender, instance, created, **kwargs):
    from kooplex.lib.filesystem import mkdir_vcpcache
    from kooplex.lib import Docker
    if created:
        mkdir_vcpcache(instance)
        Docker().trigger_impersonator(instance.vcproject) #FIXME: ne egyesevel!!

@receiver(post_delete, sender = VCProjectProjectBinding)
def archivedir_vcpcache(sender, instance, **kwargs):
    from kooplex.lib.filesystem import archivedir_vcpcache
    if len(list(instance.vcproject.vcprojectprojectbindings)) == 0:
        archivedir_vcpcache(instance.vcproject)


