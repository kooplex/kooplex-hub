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
def garbagedir_project(sender, instance, **kwargs):
    from hub.tasks import archive
    project=instance
    try:
        a1 = {
            'folder': fs.path_project(project),
            'tarbal': fs.garbage_project(project),
            'remove': True,
        }
        transaction.on_commit(lambda: archive(**a1))
    except Exception as e:
        logger.critical(e)
    try:
        a2 = {
            'folder': fs.path_report_prepare(project),
            'tarbal': fs.garbage_report_prepare(project),
            'remove': True,
        }
        transaction.on_commit(lambda: archive(**a2))
    except Exception as e:
        logger.critical(e)
