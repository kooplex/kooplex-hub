from django.contrib import messages
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User as DJUser
from django.db import models
import pwgen
import os

###from kooplex.lib.sendemail import send_new_password
from kooplex.lib.libbase import get_settings
import subprocess
from distutils.dir_util import mkpath

class User(DJUser):
    gitlab_id = models.IntegerField(null = True)
    uid = models.IntegerField(null = True)
    gid = models.IntegerField(null = True)
    bio = models.TextField(max_length = 500, blank = True)

##    data = None #dict([(k, self(k)) for k in ['first_name', 'last_name', 'username', 'email', 'password']])

    def __str__(self):
        return str(self.username)

    def __getitem__(self, k):
        if not k in self._data:
            raise Exception("Unknown attribute %s" % k)
        if self._data[k] is None:
            raise Exception("Unset attribute %s" % k)
        return self._data[k]

    def setattribute(self, **kw):
        for k, v in kw.items():
            if not k in self._data.keys():
                raise Exception("Unknown attribute: %s" % k)
            self._data[k] = v

    class Meta:
        db_table = "kooplex_hub_hubuser"

    def init(self, id):
        self.gitlab_id = id

    def get_username(self):
        return self.username

    #def create(self, request):
    def save_MEGNEEEE(self, *args, **kwargs):
        from kooplex.lib.ldap import Ldap
        l = Ldap()
        old_user = User.objects.filter(username=self.username)
        if len(old_user) == 1:
            #self = l.modify_user(old_user[0])  # FIXME: PyAsn error????
            pass # FIXME:
        else:
            pw = pwgen.pwgen(12)
            #self.username = request.POST['username']
            #self.first_name = request.POST['first_name']
            #self.last_name = request.POST['last_name']
            #self.email = request.POST['email']
            self.data = dict(username=self.username,
                           first_name=self.first_name,
                           last_name=self.last_name,
                           email=self.email,
                           password=pw)

            try:
                def mkdir(d, uid=0, gid=0, mode=0b111101000):
                    mkpath(d)
                    os.chown(d, uid, gid)
                    os.chmod(d, mode)

                self.home = "/home/" + self.username  # FIXME: this is ugly
                try:
                    self = l.add_user(self)  # FIXME:
                except Exception as e:
                    raise Exception("ldap: %s"%e) # FIXME
                    #pass

                from kooplex.lib.gitlabadmin import GitlabAdmin
                gad = GitlabAdmin()
                try:
                    msg = gad.create_user(self)
                    if len(msg):
                        raise Exception(str(msg))
                except Exception as e:
                    raise Exception(str(e))  # FIXME
                    #pass

                gg = gad.get_user(self.username)[0]
                self.gitlab_id = gg['id']

                home_dir = os.path.join(get_settings('volumes', 'home'), self.username)
                ssh_dir = os.path.join(home_dir, '.ssh')
                #oc_dir = os.path.join(home_dir, '_oc', self.username)
                git_dir = os.path.join(get_settings('volumes', 'git'), self.username)
                davfs_dir = os.path.join(home_dir, '.davfs2')

                mkdir(home_dir, uid=self.uid, gid=self.gid)
                mkdir(ssh_dir, uid=self.uid, gid=self.gid, mode=0b111000000)
                #mkdir(oc_dir, uid=self.uid, gid=self.gid, mode=0b111000000)
                mkdir(git_dir, uid=self.uid, gid=self.gid)
                mkdir(davfs_dir, uid=self.uid, gid=self.gid, mode=0b111000000)

                key_fn = os.path.join(ssh_dir, "gitlab.key")
                subprocess.call(['/usr/bin/ssh-keygen', '-N', '', '-f', key_fn])
                os.chown(key_fn, self.uid, self.gid)
                os.chown(key_fn + ".pub", self.uid, self.gid)
                key = open(key_fn + ".pub").read().strip()

                davsecret_fn = os.path.join(davfs_dir, "secrets")
                with open(davsecret_fn, "w") as f:
                    f.write(os.path.join(get_settings('owncloud', 'inner_url'), "remote.php/webdav/") + " %s %s" % (self.username, pw))


                try:
                    msg = gad.upload_userkey(self, key)
                    if len(msg):
                        raise Exception("gitkeyadd: %s" % msg)
                except Exception as e:
                    raise Exception("gitadd2: %s" % e)

                send_new_password(name = "%s %s" % (self.first_name, self.last_name),
                username = self.username,
                to = self.email,
                pw = pw)

            except Exception as e:
                error_message = "What??? %s" % str(e)
                raise CommandError(error_message)

        #self.save()
        super(User, self).save(*args, **kwargs)


    def delete(self):
        from kooplex.lib.ldap import Ldap
        l = Ldap()
        try:
            l.delete_user(self)
        except Exception as e:
            raise Exception("ldap: %s" % e)

        from kooplex.lib.gitlabadmin import GitlabAdmin
        gad = GitlabAdmin()
        try:
            gad.delete_user(self.username)
        except Exception as e:
            raise Exception("git: %s" % e)
            #pass

        super(User, self).delete()
        # TODO: remove appropriate directories from the filesystem

    def pwgen(self):
        pw = pwgen.pwgen(12)
        from kooplex.lib.ldap import Ldap
        l = Ldap()
        l.changepassword(self, 'doesntmatter', pw, validate_old_password = False)

        home_dir = os.path.join(get_settings('volume', "home"), self.username)
        davfs_dir = os.path.join(home_dir, '.davfs2')
        davsecret_fn = os.path.join(davfs_dir, "secrets")
        with open(davsecret_fn, "w") as f:
            f.write(os.path.join(get_settings('owncloud', 'inner_url'), "remote.php/webdav/") + " %s %s" % (self.username, pw))


        send_new_password(name = "%s %s" % (self.first_name, self.last_name),
           username = self.username,
           to = self.email,
           pw = pw)


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


