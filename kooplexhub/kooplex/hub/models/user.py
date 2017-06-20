from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.db import models

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
