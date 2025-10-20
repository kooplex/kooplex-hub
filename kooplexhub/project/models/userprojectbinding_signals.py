import json
import logging
import datetime

from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from kooplexhub.lib.libbase import standardize_str
from hub.models import Group, UserGroupBinding
from ..models import UserProjectBinding
import project.fs as fs

logger = logging.getLogger(__name__)


@receiver(pre_save, sender = UserProjectBinding)
def assert_single_creator(sender, instance, **kwargs):
    p = instance.project
    try:
        upb = UserProjectBinding.objects.get(project = p, role = UserProjectBinding.Role.CREATOR)
        if instance.role == UserProjectBinding.Role.CREATOR:
            assert upb.id == instance.id, "Project %s cannot have more than one creator" % p
    except UserProjectBinding.DoesNotExist:
        assert instance.role == UserProjectBinding.Role.CREATOR, "The first user project binding must be the creator %s" % instance


@receiver(pre_save, sender = UserProjectBinding)
def grantaccess_project(sender, instance, **kwargs):
    from ..tasks import grant_access
    if instance.id is None:
        is_creator = instance.role == UserProjectBinding.Role.CREATOR
        if is_creator:
            group_created=False
        else:
            group, group_created = Group.objects.get_or_create(name = instance.groupname, grouptype = Group.TP_PROJECT)
            if group_created:
                creator = UserProjectBinding.objects.get(project = instance.project, role = UserProjectBinding.Role.CREATOR).user
                UserGroupBinding.objects.get_or_create(user = instance.project.creator, group = group)
            UserGroupBinding.objects.get_or_create(user = instance.user, group = group)
        transaction.on_commit(lambda: grant_access(project=instance.project, group_created=group_created))

       

@receiver(pre_delete, sender = UserProjectBinding)
def revokeaccess_project(sender, instance, **kwargs):
    if instance.role != UserProjectBinding.Role.CREATOR:
        UserGroupBinding.objects.get(user = instance.user, group_name = instance.groupname).delete()


@receiver(pre_delete, sender = UserProjectBinding)
def assert_not_shared(sender, instance, **kwargs):
    from ..models import ProjectContainerBinding
    for pcb in ProjectContainerBinding.objects.filter(project = instance.project, container__user = instance.user):
        pcb.container.mark_restart(f"Revoked access from project {instance.project.name}")
        pcb.delete()


