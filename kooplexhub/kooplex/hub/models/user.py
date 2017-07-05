from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.db import models
import os

from kooplex.lib.libbase import get_settings

class HubUser(User):
    #user = models.OneToOneField(User, on_delete=models.CASCADE)
    #bio = models.TextField(max_length=500, blank=True)
    #location = models.CharField(max_length=30, blank=True)
    #birth_date = models.DateField(null=True, blank=True)
    gitlab_id = models.IntegerField(null=True)
    uid = models.IntegerField(null=True)
    gid = models.IntegerField(null=True)


    class Meta:
        db_table = "kooplex_hub_hubuser"

    def init(self, id):
        self.gitlab_id = id

    def get_username(self):
        return self.username

    @property
    def file_netrc_(self):
        return os.path.join(get_settings('users', 'srv_dir', None, ''), 'home', self.username, '.netrc' )

    @property
    def file_netrc_exists_(self):
        return os.path.exists(self.file_netrc_)
