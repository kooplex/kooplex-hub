import logging
import re
import base64

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding

from django.db import models
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from kooplex.lib import standardize_str

from .project import Project
from .service import Service

logger = logging.getLogger(__name__)

class VCRepository(models.Model):
    TP_GITHUB = 'github'
    TP_GITLAB = 'gitlab'
    TP_GITEA = 'gitea'
    TYPE_LIST = [ TP_GITHUB, TP_GITLAB, TP_GITEA ]

    url = models.CharField(max_length = 128, null = True)
    backend_type = models.CharField(max_length = 16, choices = [ (x, x) for x in TYPE_LIST ], default = TP_GITHUB)
    ssh_port = models.IntegerField(default = 22)

    def __str__(self):
        return self.url

    @property
    def domain(self):
        return re.split(r'https?://([^/]+)', self.url)[1]

    @register.filter
    def get_userz_vctoken(self, user):
        try:
            return VCToken.objects.get(repository = self, user = user)
        except VCToken.DoesNotExist:
            return None

class VCToken(models.Model):
    user = models.ForeignKey(User, null = False)
    repository = models.ForeignKey(VCRepository, null = False)
    username = models.CharField(max_length = 256, null = False)
    token = models.CharField(max_length = 256, null = False) # FIXME: dont store as clear text
    rsa = models.CharField(max_length = 4096, null = False, blank = True)
    last_used = models.DateTimeField(null = True, blank = True)
    error_flag = models.BooleanField(default = False, blank = True)

    @property
    def rsa_pub(self):
        private_key = serialization.load_pem_private_key(
            bytes(self.rsa, 'utf8'),
            password = None,
            backend = default_backend()
        )
        public_key = private_key.public_key()
        return public_key.public_bytes(
            encoding = serialization.Encoding.OpenSSH,
            format = serialization.PublicFormat.OpenSSH
        ).decode('utf8')

@receiver(pre_save, sender = VCToken)
def generate_rsa(sender, instance, **kwargs):
    if not instance.id and not instance.rsa:
        private_key = rsa.generate_private_key(
            public_exponent = 65537,
            key_size = 4096,
            backend = default_backend()
        )
        instance.rsa = private_key.private_bytes(
            encoding = serialization.Encoding.PEM,
            format = serialization.PrivateFormat.PKCS8,
            encryption_algorithm = serialization.NoEncryption()
        )

@receiver(post_save, sender = VCToken)
def upload_rsa(sender, instance, created, **kwargs):
    from kooplex.lib.versioncontrol import upload_rsa
    if created:
        try:
            upload_rsa(instance)
        except Exception as e:
            logger.error(f'Cannot upload rsa {instance} -- {e}')

class VCProject(models.Model):
    token = models.ForeignKey(VCToken, null = False)
    project_name = models.CharField(max_length = 512, null = False)
    project_id = models.IntegerField(null = False)
    project_description = models.TextField(null = True)
    project_created_at = models.DateTimeField(null = True)
    project_updated_at = models.DateTimeField(null = True)
    project_fullname = models.CharField(max_length = 512, null = False)
    project_owner = models.CharField(max_length = 512, null = False)
    project_ssh_url = models.CharField(max_length = 512, null = False)
    last_seen = models.DateTimeField(auto_now_add = True)
    cloned = models.BooleanField(default = False)
    clone_folder = models.CharField(max_length = 512, null = True)

    def __str__(self):
        return "VCProject %s/%s" % (self.token.repository.url, self.project_name)

    @property
    def repository(self):
        return '{}/{}'.format(self.token.repository.url, self.project_name)

    @property
    def cleanname(self):
        return standardize_str(self.project_name)

    @property
    def uniquename(self):
        t = self.token
        r = t.repository
        return "%s-%s-%s-%s" % (r.backend_type, r.domain, t.user.username, self.cleanname)

    @property
    def services(self):
        return [ b.service for b in VCProjectServiceBinding.objects.filter(vcproject = self) ]

    
class VCProjectServiceBinding(models.Model):
    vcproject = models.ForeignKey(VCProject, null = False)
    service = models.ForeignKey(Service, null = False)

    class Meta:
        unique_together = [['vcproject', 'service']]
##
##    @staticmethod
##    def getbinding(user, project):
##        for b in VCProjectProjectBinding.objects.filter(project = project):
##            if b.vcproject.token.user == user:
##                yield b
##
##    @property
##    def otherprojects(self):
##        for b in VCProjectProjectBinding.objects.filter(vcproject = self.vcproject):
##            yield b.project
##

#FIXME: obsoleted
##@receiver(post_save, sender = VCProjectProjectBinding)
##def mkdir_vcpcache(sender, instance, created, **kwargs):
##    from kooplex.lib.filesystem import mkdir_vcpcache
##    from kooplex.lib import Docker
##    if created:
##        mkdir_vcpcache(instance)
##        Docker().trigger_impersonator(instance.vcproject) #FIXME: ne egyesevel!!
##
##@receiver(post_delete, sender = VCProjectProjectBinding)
##def archivedir_vcpcache(sender, instance, **kwargs):
##    from kooplex.lib.filesystem import archivedir_vcpcache
##    if len(list(instance.vcproject.vcprojectprojectbindings)) == 0:
##        archivedir_vcpcache(instance.vcproject)


