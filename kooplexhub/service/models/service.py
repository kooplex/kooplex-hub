import logging
import unidecode
import os

from django.db import models
from django.db.models.signals import pre_save , post_save#, pre_delete, post_delete
from django.dispatch import receiver

from django.contrib.auth.models import User

#from hub.models.token import Token
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
    kubernetes_secret_name = models.CharField(max_length = 64, null = True, default="seafile-vo-elte-hu")
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
        
    # def _check_secret_exists(self, user):
    #     try:
    #         secret = v1.read_namespaced_secret(name=self.kubernetes_secret_name, namespace=KOOPLEX['kubernetes'].get('namespace'))
    #     except client.exceptions.ApiException:
    #         v1.create_namespaced_secret(body=client.V1Secret(metadata={'name':self.kubernetes_secret_name}), namespace=KOOPLEX['kubernetes'].get('namespace'))
    #         return
        
    # def check_usersecret_exists(self, user):
    #     try:
    #         secret = v1.read_namespaced_secret(name=self.kubernetes_secret_name, namespace=KOOPLEX['kubernetes'].get('namespace'))
    #         user_secret = secret.data.get(username)
    #         if user_secret:
    #             return user_secret
    #         else:
    #             pw = self.create_pw(user)
    #             secret.string_data = {user.username: pw}
    #             v1.patch_namespaced_secret(name=self.kubernetes_secret_name, namespace=KOOPLEX['kubernetes'].get('namespace'), body=body)
    #     #except client.exceptions.ApiException:
    #     except:
    #         v1.create_namespaced_secret(body=client.V1Secret(metadata={'name':self.kubernetes_secret_name}), namespace=KOOPLEX['kubernetes'].get('namespace'))
    
    def sync_pw(self, user):
        import requests, pwgen, json, base64
        from api.kube import update_user_secret, get_user_secrets
        # get user's secret
        secrets = get_user_secrets(user, token_key=self.kubernetes_secret_name)
        secret_set = set(secrets.values())
        if len(secret_set) == 1:
            encoded_token = secret_set.pop()
            if encoded_token:
                token = base64.b64decode(encoded_token)
            else:
                # Seafile PW shouldn't be too long
                token = pwgen.pwgen(12)
        else:
            # Seafile PW shouldn't be too long
            token = pwgen.pwgen(12)

        logger.debug(f"{token}")
        # Get admin token
        url = os.path.join(KOOPLEX['seafile'].get('url_api'), 'auth-token') + "/"
        data = {'username': KOOPLEX['seafile'].get('admin'), 'password': KOOPLEX['seafile'].get('admin_password')}
        resp = requests.post(url=url, data=data)
        assert resp.ok, "Cannot retrieve admin token"
        admin_token = json.loads(resp.content.decode())['token']
        # store user pw in seafile
        url = os.path.join(KOOPLEX['seafile'].get('url_api'), 'accounts', user.email) + "/"
        headers = {'Authorization': f"Token {admin_token}"}
        data = {'password': token}
        resp = requests.put(url=url, headers=headers, data=data)
        # store secret in kubernetes namespace(s)
        if len(secret_set) != 1:
            kube_secret = { self.kubernetes_secret_name: token }
            update_user_secret(user, kube_secret)
            
    
#class UserSeafileServiceBinding(models.Model):  
#    user = models.ForeignKey(User, on_delete = models.CASCADE)
#    service = models.ForeignKey(SeafileService, on_delete = models.CASCADE)
#    token = models.ForeignKey(Token, on_delete = models.CASCADE, null=True)
    
#@receiver(post_save, sender = UserSeafileServiceBinding)
#def create_pw(sender, instance, **kwargs):
#    from api.kube import update_user_secret
#    token = {instance.service.kubernetes_secret_name: instance.service.create_pw(instance.user)}
#    update_user_secret(instance.user, token)
    
    
