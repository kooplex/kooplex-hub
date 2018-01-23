import logging
import os
import pwgen

from django.contrib import messages
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User as DJUser
from django.db import models

from kooplex.lib import get_settings

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
    def n_projects(self):
        from .project import Project
        return len(list(Project.objects.filter(owner = self)))

    def projects(self):
        from .project import Project
        for p in Project.objects.filter(owner = self):
            yield p

    @property
    def n_reports(self):
        from .report import Report
        return len(list(Report.objects.filter(creator = self)))

    @property
    def fn_tokenfile(self):
        return get_settings('user', 'pattern_tokenfile') % self

    def sendtoken(self):
        from kooplex.lib.sendemail import send_token
        token = pwgen.pwgen(12)
        with open(self.fn_tokenfile, 'w') as f:
            f.write(token)
        send_token(self, token)

    def is_validtoken(self, token):
        try:
            return token == open(self.fn_tokenfile).read()
        except: #File missing
            return False

    def changepassword(self, password):
        from kooplex.lib.filesystem import write_davsecret
        self.password = password
        write_davsecret(self)
        self.save()

    def generatenewpassword(self):
        password = pwgen.pwgen(12)
        self.changepassword(self, password)
        with open(get_settings('user', 'pattern_passwordfile') % self, 'w') as f:
            f.write(self.password)
        self.changepassword(password)
        #FIXME: send e-mail

    def researchgroups(self):
        for rpb in ResearchgroupProjectBinding.objects.filter(user = self):
            yield rpb.researchgroup

    def create(self, skip_gitlab = False):
        from kooplex.logic import user
        logger.debug("%s" % self)
        # set uid and gid, generate token
        self.uid = User.objects.all().aggregate(models.Max('uid'))['uid__max'] + 1
        self.gid = get_settings('ldap', 'usersgroupid')
        self.token = pwgen.pwgen(64)
        # during user manifestation gitlab_id and password are set
        status = user.add(self, skip_gitlab)
        self.save()
        logger.info(("New user: %(last_name)s %(first_name)s (%(username)s with uid/gitlab_id: %(uid)d/%(gitlab_id)d) created. Email: %(email)s) status: " % self) + "{0:b}".format(status))

    def remove(self):
        from kooplex.logic import user
        logger.debug("%s" % self)
        status = user.remove(self)
        logger.info(("Deleted user: %(last_name)s %(first_name)s (%(username)s with uid/gitlab_id: %(uid)d/%(gitlab_id)d) created. Email: %(email)s) status: " % self) + "{0:b}".format(status))
#        self.delete()

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


