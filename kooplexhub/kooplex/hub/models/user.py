import logging
import pwgen
import os
import subprocess
from distutils.dir_util import mkpath

from django.contrib import messages
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User as DJUser
from django.db import models

from kooplex.lib import get_settings, mkdir_homefolderstructure
from kooplex.lib import send_new_password, send_token
from kooplex.lib import write_davsecret, generate_rsakey, read_rsapubkey
from kooplex.lib import Ldap, GitlabAdmin

logger = logging.getLogger(__name__)

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

    def save(self, **kw):
        try:
            User.objects.get(username = self.username)
            DJUser.save(self, **kw)
            return
        except User.DoesNotExist:
            # we need to create the account right now
            pass
        errors = 0
        # generate uid and gid
        next_uid = User.objects.all().aggregate(models.Max('uid'))['uid__max'] + 1
        self.uid = next_uid
        self.gid = get_settings('ldap', 'usersgroupid')
        # generate password and token
        self.password = pwgen.pwgen(12)
        with open(get_settings('user', 'pattern_passwordfile') % self, 'w') as f:
            f.write(self.password)
        self.token = pwgen.pwgen(64)
        # create new ldap entry
        try:
            Ldap().adduser(self)
        except Exception as e:
            logger.error("Failed to create ldap entry for %s (%s)" % (self, e))
            errors |= 0x000001
        # create home filesystem
        try:
            mkdir_homefolderstructure(self)
        except Exception as e:
            logger.error("Failed to create home for %s (%s)" % (self, e))
            errors |= 0x000010
        # create gitlab account
        try:
            gad = GitlabAdmin()
            gad.create_user(self)
        except Exception as e:
            logger.error("Failed to create gitlab entry for %s (%s)" % (self, e))
            errors |= 0x000100
        # retrieve gitlab_id
        try:
            data = gad.get_user(self)[0]
            self.gitlab_id = data['id']
        except Exception as e:
            logger.error("Failed to fetch gitlab id for %s (%s)" % (self, e))
            errors |= 0x001000
        # generate and upload rsa key
        try:
            generate_rsakey(self)
            pub_key_content = read_rsapubkey(self)
            gad.upload_userkey(self, pub_key_content)
        except Exception as e:
            logger.error("Failed to upload rsa key in gitlab for %s (%s)" % (self, e))
            errors |= 0x010000
            raise
        # send email with the password
        if send_new_password(self) != 0:
            logger.error("Failed to send email to %s (%s)" % (self, self.email))
            errors |= 0x100000
        # send summary report to admin
        DJUser.save(self)
        logger.info("New user: %s %s (%s with uid/gid: %d/%s) created. Email: %s (Errorflags: %s)" % (self.last_name, self.first_name, self.username, self.uid, self.gid, self.email, "{0:b}".format(errors)))

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


