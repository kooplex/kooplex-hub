import logging
import re

from django.db import models
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.template.defaulttags import register

from kooplex.lib import standardize_str

from .service import Service

logger = logging.getLogger(__name__)

class FSServer(models.Model):
    TP_SEAFILE = 'seafile'
    TYPE_LIST = [ TP_SEAFILE ]

    url = models.CharField(max_length = 128, null = True)
    backend_type = models.CharField(max_length = 16, choices = [ (x, x) for x in TYPE_LIST ], default = TP_SEAFILE)

    def __str__(self):
        return self.url

    @property
    def domain(self):
        return re.split(r'https?://([^/]+)', self.url)[1]

    @register.filter
    def get_usertoken(self, user):
        try:
            return FSToken.objects.get(syncserver = self, user = user)
        except FSToken.DoesNotExist:
            return None

class FSToken(models.Model):
    user = models.ForeignKey(User, null = False)
    syncserver = models.ForeignKey(FSServer, null = False)
    token = models.CharField(max_length = 256, null = False) # FIXME: dont store as clear text
    last_used = models.DateTimeField(null = True, default = None)
    error_flag = models.BooleanField(default = False)       # TODO: save error message maybe stored in a separate table


class FSLibrary(models.Model):
    token = models.ForeignKey(FSToken, null = False)
    library_name = models.CharField(max_length = 512, null = False)
    library_id = models.CharField(max_length = 36, null = False)
    last_seen = models.DateTimeField(auto_now_add = True)
    syncing = models.BooleanField(default = False)
    sync_folder = models.CharField(max_length = 512, null = False)

    class Meta:
        unique_together = [['token', 'library_id']]

    def __str__(self):
        return "FSLibrary %s: %s" % (self.token.syncserver.url, self.library_name)

    @property
    def cleanname(self):
        return standardize_str(self.library_name)

    @property
    def uniquename(self):
        t = self.token
        s = t.syncserver
        return "%s-%s-%s-%s" % (s.backend_type, s.domain, t.user.username, self.cleanname)

    @property
    def services(self):
        return [ b.service for b in FSLibraryServiceBinding.objects.filter(fslibrary = self) ]

    
class FSLibraryServiceBinding(models.Model):
    fslibrary = models.ForeignKey(FSLibrary, null = False)
    service = models.ForeignKey(Service, null = False)

    class Meta:
        unique_together = [['fslibrary', 'service']]

#    @staticmethod
#    def getbinding(user, project):
#        for b in FSLibraryProjectBinding.objects.filter(project = project):
#            if b.fslibrary.token.user == user:
#                yield b
#
#    @property
#    def otherprojects(self):
#        for b in FSLibraryProjectBinding.objects.filter(fslibrary = self.fslibrary):
#            yield b.project


##@receiver(post_save, sender = FSLibraryProjectBinding)
##def mkdir_fslcache(sender, instance, created, **kwargs):
##    raise NotImplementedError
# sync = True
##    from kooplex.lib.filesystem import mkdir_vcpcache
##    from kooplex.lib import Docker
##    if created:
##        mkdir_vcpcache(instance)
##        Docker().trigger_impersonator(instance.vcproject) #FIXME: ne egyesevel!!

##@receiver(post_delete, sender = FSLibraryProjectBinding)
##def archivedir_vcpcache(sender, instance, **kwargs):
##    from kooplex.lib.filesystem import archivedir_vcpcache
##    if len(list(instance.vcproject.vcprojectprojectbindings)) == 0:
##        archivedir_vcpcache(instance.vcproject)


