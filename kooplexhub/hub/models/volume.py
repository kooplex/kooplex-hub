import logging
import re
import os

from django.db import models
from django.contrib.auth.models import User

from .project import Project
from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Volume(models.Model):
    volumeconf = KOOPLEX.get('docker', {}) #FIXME: namespace
    HOME = {
        'tag': 'home', 
        'description': 'Home volume',
        'pattern': volumeconf.get('pattern_homevolumename_filter', r'^(home)$'),
    }
    SHARE = {
        'tag': 'share', 
        'description': 'Share volume',
        'pattern': volumeconf.get('pattern_sharevolumename_filter', r'^(share)$'),
    }
    WORKDIR = {
        'tag': 'workdir', 
        'description': 'Workdir volume',
        'pattern': volumeconf.get('pattern_workdirvolumename_filter', r'^(workdir)$'),
    }
    FUNCTIONAL = {
        'tag': 'functional', 
        'description': 'Functional volume',
        'pattern': volumeconf.get('pattern_functionalvolumename_filter', r'^fun-(\w+)$'),
    }
    STORAGE = {
        'tag': 'storage', 
        'description': 'Storage volume',
        'pattern': volumeconf.get('pattern_storagevolumename_filter', r'^stg-(\w+)$'),
    }
    COURSE_SHARE = {
        'tag': 'course', 
        'description': 'Course share volume',
        'pattern': volumeconf.get('pattern_coursevolumename_filter', r'^(course)$'),
    }
    COURSE_WORKDIR = {
        'tag': 'usercourse', 
        'description': 'Course workdir volume',
        'pattern': volumeconf.get('pattern_usercoursevolumename_filter', r'^(usercourse)$'),
    }
    COURSE_ASSIGNMENTDIR = {
        'tag': 'assignment', 
        'description': 'Course assignment volume',
        'pattern': volumeconf.get('pattern_assignmentvolumename_filter', r'^(assignment)$'),
    }
    VOLUME_TYPE_LIST = [HOME, SHARE, WORKDIR, FUNCTIONAL, STORAGE, COURSE_SHARE, COURSE_WORKDIR, COURSE_ASSIGNMENTDIR]
    name = models.CharField(max_length = 64, unique = True)
    displayname = models.CharField(max_length = 64)
    description = models.TextField(null = True)
    volumetype = models.CharField(max_length = 16, choices = [ (x['tag'], x['tag']) for x in VOLUME_TYPE_LIST ])
    is_present = models.BooleanField(default = True)

    def __str__(self):
        return self.displayname

    @staticmethod
    def try_create(volumename):
        for x in Volume.VOLUME_TYPE_LIST:
            pattern = x['pattern']
            if re.match(pattern, volumename):
                _, dirname, _ = re.split(pattern, volumename)
                return Volume.objects.create(name = volumename, displayname = dirname, description = '%s (%s)' % (x['description'], dirname), volumetype = x['tag'])

    @staticmethod
    def lookup(volumetype, **kw): #FIXME: check if still used somewhere
        if not volumetype in Volume.VOLUME_TYPE_LIST:
            raise Volume.DoesNotExist
        return Volume.objects.get(volumetype = volumetype['tag'], **kw)

    @staticmethod
    def filter(volumetype, **kw):
        if not volumetype in Volume.VOLUME_TYPE_LIST:
            raise Volume.DoesNotExist
        user = kw.pop('user', None)
        if user:
            logger.error("NotImplementedError") #FIXME
            pass
        for volume in Volume.objects.filter(volumetype = volumetype['tag'], **kw):
            yield volume

    def is_volumetype(self, volumetype):
        try:
            return self.volumetype == volumetype['tag']
        except KeyError:
            return False

    def mode(self, user):
        if self.is_volumetype(Volume.FUNCTIONAL):
            for binding in VolumeOwnerBinding.objects.filter(volume = self):
                if binding.owner == user:
                    return 'rw'
            return 'ro'
        if self.is_volumetype(Volume.STORAGE):
            if hasattr(self, 'extrafields'):
                return 'rw' if self.extrafields.readwrite else 'ro'
            else:
                return 'ro'
        return 'rw'

    @property
    def mountpoint(self):
        for x in Volume.VOLUME_TYPE_LIST:
            if x['tag'] == self.volumetype:
                break
        _, dirname, _ = re.split(x['pattern'], self.name)
        if self.is_volumetype(Volume.FUNCTIONAL):
            return self.volumeconf.get('pattern_functional_mnt', '/vol/%(name)s') % { 'name': dirname }
        if self.is_volumetype(Volume.STORAGE):
            return self.volumeconf.get('pattern_functional_mnt', '/data/%(name)s') % { 'name': dirname }
        return self.volumeconf.get('pattern_mnt', '/mnt/.volumes/%(name)s') % { 'name': dirname }


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


def init_model():
    from kooplex.lib import Docker
    dockerconf = KOOPLEX.get('docker', {})
    for volume in Volume.objects.all():
        volume.is_present = False
        volume.save()
    for volumename in Docker().list_volumenames():
        logger.debug("vol: %s" % volumename)
        try:
            volume = Volume.objects.get(name = volumename)
            volume.is_present = True
        except Volume.DoesNotExist:
            volume = Volume.try_create(volumename)
            if volume:
                logger.debug("created %s" % volume)

