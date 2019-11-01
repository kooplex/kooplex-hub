import logging
import re
import os

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from .project import Project
from .course import Course
from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

TYPE_LOOKUP = {
  'home': 'Home volume',
  'garbage': 'Garbage volume',
  'report': 'Report volume',
  'share': 'Share volume',
  'workdir': 'Workdir volume',
  'git': 'Git cache volume',
  'filesync': 'File synchronization cache volume',
  'functional': 'Functional volume',
  'storage': 'Storage volume',
  'course': 'Course share volume',
  'usercourse': 'Course workdir volume',
  'assignment': 'Course assignment volume',
  'private' : 'User created and private',
}

class Volume(models.Model):
    pattern = KOOPLEX.get('volumepattern', {})

    HOME = 'home'
    GARBAGE = 'garbage'
    GIT = 'git'
    FILESYNC = 'filesync'
    SHARE = 'share'
    WORKDIR = 'workdir'
    FUNCTIONAL = 'functional'
    STORAGE = 'storage'
    PRIVATE = 'private'
    COURSE_SHARE = 'course'
    COURSE_WORKDIR = 'usercourse'
    COURSE_ASSIGNMENTDIR = 'assignment'
    REPORT = 'report'
    VOLUME_TYPE_LIST = [ HOME, GARBAGE, GIT, FILESYNC, SHARE, WORKDIR, FUNCTIONAL, STORAGE, COURSE_SHARE, COURSE_WORKDIR, COURSE_ASSIGNMENTDIR, REPORT, PRIVATE ]
    VOLUME_TYPE_LIST_USER = [ FUNCTIONAL ]#, STORAGE, PRIVATE ]

    name = models.CharField(max_length = 64, unique = True)
    displayname = models.CharField(max_length = 64)
    description = models.TextField(null = True)
    volumetype = models.CharField(max_length = 16, choices = [ (x, TYPE_LOOKUP[x]) for x in VOLUME_TYPE_LIST ])
    is_present = models.BooleanField(default = True)

    def __str__(self):
        return self.displayname

    @staticmethod
    def try_create(volumename):
        for x in Volume.VOLUME_TYPE_LIST:
            pattern = Volume.pattern.get(x, r'^(%s)$' % x)
            if re.match(pattern, volumename):
                _, dirname, _ = re.split(pattern, volumename)
                return Volume.objects.create(name = volumename, displayname = dirname, description = '%s (%s)' % (TYPE_LOOKUP[x], dirname), volumetype = x)

#    @staticmethod
#    def lookup(volumetype, **kw): #FIXME: check if still used somewhere
#        if not volumetype in Volume.VOLUME_TYPE_LIST:
#            raise Volume.DoesNotExist
#        return Volume.objects.get(volumetype = volumetype['tag'], **kw)

    @staticmethod
    def filter(volumetype, **kw):
        if not volumetype in Volume.VOLUME_TYPE_LIST:
            raise Volume.DoesNotExist
        user = kw.pop('user', None)
        if user:
            logger.error("NotImplementedError") #FIXME
            pass
        for volume in Volume.objects.filter(volumetype = volumetype, **kw):
            yield volume

#    def is_volumetype(self, volumetype):
#        try:
#            return self.volumetype == volumetype['tag']
#        except KeyError:
#            return False

    def mode(self, user):
        if self.volumetype == Volume.FUNCTIONAL:
            for binding in VolumeOwnerBinding.objects.filter(volume = self):
                if binding.owner == user:
                    return 'rw'
            return 'ro'
        if self.volumetype == Volume.STORAGE:
            if hasattr(self, 'extrafields'):
                return 'rw' if self.extrafields.readwrite else 'ro'
            else:
                return 'ro'
        return 'rw'

    @property
    def mountpoint(self):
        pattern = self.pattern.get(self.volumetype, r'^(%s)$' % self.volumetype)
        _, dirname, _ = re.split(pattern, self.name)
        if self.volumetype == Volume.FUNCTIONAL:
            return os.path.join('/vol', dirname)
        if self.volumetype == Volume.STORAGE:
            return os.path.join('/data', dirname)
        return os.path.join('/mnt/.volumes', dirname)

@receiver(pre_save, sender = Volume)
def create_volume(sender, instance, **kwargs):
    from kooplex.lib import Docker
    try:
        docker = Docker()
        docker.create_volume(instance)

        logger.INFO("Volume %s created"%instance.name) 
    except :
        logger.error("NotImplementedError")
        pass

@receiver(pre_delete, sender = Volume)
def delete_volume(sender, instance, **kwargs):
    from kooplex.lib import Docker
    try:
        docker = Docker()
        docker.delete_volume(instance)

        logger.info("Volume %s deleted"%instance.name) 
    except Exception as e:
        logger.info(" %s "%e) 
        logger.error("NotImplementedError")
        pass

class VolumeOwnerBinding(models.Model):
    volume = models.ForeignKey(Volume, null = True)
    owner = models.ForeignKey(User, null = True)


class ExtraFields(models.Model):
    volume = models.OneToOneField(Volume)#, on_delete = models.CASCADE)
    groupid = models.IntegerField(null = True)
    public = models.BooleanField(default = False)
    is_writable = models.BooleanField(default = False)


class UserPrivilegeVolumeBinding(models.Model):
    volume = models.ForeignKey(Volume, null = True)
    user = models.ForeignKey(User, null = True)
    readwrite = models.BooleanField(default = False)

    def __str__(self):
        return "%s@%s" % (self.user, self.volume)


class VolumeProjectBinding(models.Model):
    volume = models.ForeignKey(Volume, null = False)
    project = models.ForeignKey(Project, null = False)
    #readwrite = models.BooleanField(default = False)

    def __str__(self):
       return "%s-%s" % (self.project.name, self.volume.name)


class VolumeCourseBinding(models.Model):
    volume = models.ForeignKey(Volume, null = False)
    course = models.ForeignKey(Course, null = False)

    def __str__(self):
       return "%s-%s" % (self.course.name, self.volume.name)


