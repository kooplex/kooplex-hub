import json
import logging
import datetime

from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from kooplexhub.lib.libbase import standardize_str
from hub.models import Group, UserGroupBinding
from hub.models import Task
from ..models import UserProjectBinding
from .. import filesystem as fs

logger = logging.getLogger(__name__)


@receiver(pre_save, sender = UserProjectBinding)
def assert_single_creator(sender, instance, **kwargs):
    p = instance.project
    try:
        upb = UserProjectBinding.objects.get(project = p, role = UserProjectBinding.RL_CREATOR)
        if instance.role == UserProjectBinding.RL_CREATOR:
            assert upb.id == instance.id, "Project %s cannot have more than one creator" % p
    except UserProjectBinding.DoesNotExist:
        assert instance.role == UserProjectBinding.RL_CREATOR, "The first user project binding must be the creator %s" % instance


@receiver(pre_save, sender = UserProjectBinding)
def grantaccess_project(sender, instance, **kwargs):
    p = instance.project
    if instance.id is None:
        is_creator = instance.role == UserProjectBinding.RL_CREATOR
        if is_creator:
            acl = { 'users_rw': [instance.user.id] }
            creator_username = instance.user.username
        else:
            creator_username = p.creator.username
            with transaction.atomic():
                group, group_created = Group.objects.select_for_update().get_or_create(name = instance.groupname, grouptype = Group.TP_PROJECT)
            if group_created:
                creator = UserProjectBinding.objects.get(project = instance.project, role = UserProjectBinding.RL_CREATOR).user
                UserGroupBinding.objects.create(user = creator, group = group)
                acl = { 'groups_rw': [group.id] }
            else:
                acl = None
            UserGroupBinding.objects.create(user = instance.user, group = group)
        if acl:
            Task(
                create = True,
                name = f"Grant access {p.name}({creator_username}) to {instance.user.username}",
                task = "project.tasks.grant_access",
                kwargs = {
                    'folders': [ fs.path_project(p), fs.path_report_prepare(p) ],
                    'acl': acl,
                }
            )
       

@receiver(pre_delete, sender = UserProjectBinding)
def revokeaccess_project(sender, instance, **kwargs):
    if instance.role != UserProjectBinding.RL_CREATOR:
        group = Group.objects.get(name = instance.groupname, grouptype = Group.TP_PROJECT)
        UserGroupBinding.objects.get(user = instance.user, group = group).delete()
        Task(
            create = True,
            name = f"Revoke access {instance.project.name}({instance.project.creator.username}) from {instance.user.username}",
            task = "project.tasks.revoke_access",
            kwargs = {
                'folders': [ fs.path_project(instance.project), fs.path_report_prepare(instance.project) ],
                'user_id': instance.user.id,
            }
        )


@receiver(pre_delete, sender = UserProjectBinding)
def assert_not_shared(sender, instance, **kwargs):
    from ..models import ProjectContainerBinding
    for pcb in ProjectContainerBinding.objects.filter(project = instance.project, container__user = instance.user):
        pcb.container.mark_restart(f"Revoked access to project {instance.project.name}")
        pcb.delete()


@receiver(pre_delete, sender = UserProjectBinding)
def garbagedir_project(sender, instance, **kwargs):
    if instance.role != UserProjectBinding.RL_CREATOR:
        return
    Task(
        create = True,
        name = f"Garbage project {instance.id}",
        task = "kooplexhub.tasks.create_tar",
        kwargs = {
            'folder': fs.path_project(instance.project), 
            'tarbal': fs.garbage_project(instance.project),
        }
    )
    Task(
        create = True,
        name = f"Garbage report prepare {instance.id}",
        task = "kooplexhub.tasks.create_tar",
        kwargs = {
            'folder': fs.path_report_prepare(instance.project),
            'tarbal': fs.garbage_report_prepare(instance.project),
        }
    )
