from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User
from django.db import models

class HubUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    #bio = models.TextField(max_length=500, blank=True)
    #location = models.CharField(max_length=30, blank=True)
    #birth_date = models.DateField(null=True, blank=True)
    gitlab_id = models.IntegerField(null=True)


    def init(self, id, user):
        self.gitlab_id = id
        self.user = user

    def get_username(self):
        return self.user.username()
