import logging
import unidecode
import os

from django.db import models
from django.db.models.signals import pre_save #, post_save, pre_delete, post_delete
from django.dispatch import receiver

from django.contrib.auth.models import User

from hub.models.token import Token
from kooplexhub.settings import KOOPLEX

#from jsonfield import JSONField

logger = logging.getLogger(__name__)


# class ServiceType(models.Model):  
#     S_CLOUD = 'cloud service'
#     S_VC = 'version control'
#     T_LOOKUP = {
#         S_CLOUD: 'Cloud file sharing (Dropbox, Seafile, Nextcloud etc...)',
#         S_VC = 'Version Control System (Github, Gitea)',
#     }
    
# A row per user per Service
class SeafileService(models.Model):  
    #name = models.CharField(max_length = 64, null = True) # unique?
    #service_type = models.CharField(max_length = 32, choices = T_LOOKUP.items())
    
    #mount_dir = models.CharField(max_length = 64, null = False) 
    kubernetes_secret_name = models.CharField(max_length = 64, null = True, default="seafile-secret")
    url = models.CharField(max_length = 256, null = False)
 
    @property
    def hostname(self):
        from urllib.parse import urlparse
        return urlparse(self.url).netloc
    
    def __str__(self):
        return self.hostname
    
    @property
    def mount_dir(self):
        return f"/v/cloud-{self.hostname}"

    @property
    def secret_mount_dir(self):
        return KOOPLEX['kubernetes']['secrets'].get("mount_dir", "/.secrets")
    
    @property
    def secret_file(self):
        return ".davfs"
    
    def get_envs(self, user):
        envs_dict = {
        "WEBDRIVE_MOUNT" : self.mount_dir,
        "WEBDRIVE_USERNAME": user.email,
        "WEBDRIVE_PASSWORD_FILE": os.path.join(self.secret_mount_dir, self.secret_file),
        "WEBDRIVE_URL": self.url,
        "OWNER":  f"{user.profile.userid}"
        }   
        return [ {'name':key, "value": val} for key, val in envs_dict.items()]    
        
    def create_pw(self):
        # Get admin token
        ### curl -d "username=kooplex@elte.hu" -d "password=Cut3chohSiepa4vu" https://seafile.vo.elte.hu/api2/auth-token/
        # create pw for user
        ### curl  -X PUT -d "password=proba321" -H "Authorization: Token 185f3819c20bf8fa5b169ed30e8d5cbc73c9468c" -H "Accept: application/json; indent=4" https://seafile.vo.elte.hu/api2/accounts/jozsef.steger@ttk.elte.hu/
        # Then put it among the kubernetes secrets
        token="proba3211"
        return token
            
    # @property
    # def kubernetes_secret_name(self):
    #     return "seafile-secret"
    
class UserSeafileServiceBinding(models.Model):  
    user = models.ForeignKey(User, on_delete = models.CASCADE)
    service = models.ForeignKey(SeafileService, on_delete = models.CASCADE)
    token = models.ForeignKey(Token, on_delete = models.CASCADE, null=True)
    
receiver(pre_save, sender = UserSeafileServiceBinding)
def create_pw(sender, instance, **kwargs):
    # FIXME
    token.objects.get_or_create(value = instance.create_pw())
    