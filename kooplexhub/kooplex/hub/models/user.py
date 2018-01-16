import pwgen
import os
import subprocess
from distutils.dir_util import mkpath

from django.contrib import messages
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User as DJUser
from django.db import models

from kooplex.lib import get_settings
from kooplex.lib.sendemail import send_new_password, send_token
from kooplex.lib.filesystem import write_davsecret
from kooplex.lib.lldap import Ldap #FIXME: to be renamed ldap

class User(DJUser):
    gitlab_id = models.IntegerField(null = True)
    uid = models.IntegerField(null = True)
    gid = models.IntegerField(null = True)
    bio = models.TextField(max_length = 500, blank = True)
    token = models.CharField(max_length = 64, null = True)

    def __str__(self):
        return str(self.username)

    def __lt__(self, u):
        return self.first_name < u.first_name if self.last_name == u.last_name else self.last_name < u.last_name

    def __getitem__(self, k):
        return self.__getattribute__(k)

    @property
    def fn_tokenfile(self):
        return get_settings('user', 'pattern_tokenfile') % self

    def sendtoken(self):
        token = pwgen.pwgen(12)
        with open(self.fn_tokenfile, 'w') as f:
            f.write(token)
        send_token(self, token)

    def is_validtoken(self, token):
        try:
            return token == open(self.fn_tokenfile).read()
        except: #File missing
            return False

    def is_validpassword(self, password):
        return Ldap().is_validpassword(self, password)

    def changepassword(self, newpassword, oldpassword = None):
        l = Ldap()
        l.changepassword(self, newpassword, oldpassword)
        self.password = newpassword
        write_davsecret(self)
        self.save()

    def researchgroups(self):
        for rpb in ResearchgroupProjectBinding.objects.filter(user = self):
            yield rpb.researchgroup
            

class Researchgroup(models.Model):
    id = models.AutoField(primary_key = True)
    name = models.CharField(max_length = 32)
    description = models.TextField(max_length = 500, null = True)

    def __str__(self):
       return self.name

class ResearchgroupUserBinding(models.Model):
    id = models.AutoField(primary_key = True)
    user = models.ForeignKey(User, null = False)
    researchgroup = models.ForeignKey(Researchgroup, null = False)

    def __str__(self):
       return "%s@%s" % (self.user, self.researchgroup)


