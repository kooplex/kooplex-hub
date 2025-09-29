import json
import logging
import datetime

from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from kooplexhub.lib.libbase import standardize_str
from hub.models import Group, UserGroupBinding
from hub.tasks import delete_folder
from hub.lib.filesystem import _mkdir
from ..models import Project
import project.fs as fs

logger = logging.getLogger(__name__)


@receiver(pre_save, sender = Project)
def mkdir_project(sender, instance, **kwargs):
    if instance.id is None:
        cleanname = standardize_str(instance.name)
        if instance.subpath is None:
            instance.subpath = f'{cleanname}-{instance.creator.username}'
        _mkdir(fs.path_project(instance))
        _mkdir(fs.path_report_prepare(instance))
       

@receiver(pre_delete, sender = Project)
def rmdir_project(sender, instance, **kwargs):
    try:
        #FIXME: Group.objects.get(name = instance.groupname, grouptype = Group.TP_PROJECT).delete()
        pass
    except Group.DoesNotExist:
        pass
    delete_folder(fs.path_project(instance))
    delete_folder(fs.path_report_prepare(instance))
