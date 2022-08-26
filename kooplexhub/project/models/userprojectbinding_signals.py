import json
import logging
import datetime

from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from django_celery_beat.models import ClockedSchedule, PeriodicTask
from kooplexhub.lib.libbase import standardize_str
from hub.models import Group, UserGroupBinding
from ..models import UserProjectBinding
from .. import filesystem as fs

logger = logging.getLogger(__name__)

code = lambda x: json.dumps([ i.id for i in x ])


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
def mkdir_project(sender, instance, **kwargs):
    p = instance.project
    if instance.id is None:
        cleanname = standardize_str(p.name)
        if p.subpath is None:
            p.subpath = f'{cleanname}-{instance.user.username}'
            p.save()
        is_creator = instance.role == UserProjectBinding.RL_CREATOR
        if not is_creator:
            with transaction.atomic():
                group, group_created = Group.objects.select_for_update().get_or_create(name = instance.groupname, grouptype = Group.TP_PROJECT)
            if group_created:
                creator = UserProjectBinding.objects.get(project = instance.project, role = UserProjectBinding.RL_CREATOR).user
                UserGroupBinding.objects.create(user = creator, group = group)
                acl = { 'groups_rw': [group.id] }
            else:
                acl = None
            UserGroupBinding.objects.create(user = instance.user, group = group)
        else:
            acl = { 'users_rw': [instance.user.id] }
        if acl:
            schedule_now = ClockedSchedule.objects.create(clocked_time = datetime.datetime.now())
            PeriodicTask.objects.create(
                name = f"grant_access_{p.subpath}_{instance.user.username}",
                task = "project.tasks.manage_folder",
                clocked = schedule_now,
                one_off = True,
                kwargs = json.dumps({
                    'create_folder': is_creator,
                    'folders': [ fs.path_project(p), fs.path_report_prepare(p) ],
                    'acl': acl,
                })
            )
       

@receiver(pre_delete, sender = UserProjectBinding)
def revokeaccess_project(sender, instance, **kwargs):
    if instance.role != UserProjectBinding.RL_CREATOR:
        group = Group.objects.get(name = instance.groupname, grouptype = Group.TP_PROJECT)
        UserGroupBinding.objects.get(user = instance.user, group = group).delete()
        schedule_now = ClockedSchedule.objects.create(clocked_time = datetime.datetime.now())
        PeriodicTask.objects.create(
            name = f"revoke_access_{instance.id}",
            task = "project.tasks.revoke_access",
            clocked = schedule_now,
            one_off = True,
            kwargs = json.dumps({
                'folders': [ fs.path_project(instance.project), fs.path_report_prepare(instance.project) ],
                'user_id': instance.user.id,
            })
        )


@receiver(pre_delete, sender = UserProjectBinding)
def garbagedir_project(sender, instance, **kwargs):
    if instance.role == UserProjectBinding.RL_CREATOR:
        try:
            Group.objects.get(name = instance.groupname, grouptype = Group.TP_PROJECT).delete()
        except Group.DoesNotExist:
            pass
        schedule_now = ClockedSchedule.objects.create(clocked_time = datetime.datetime.now())
        PeriodicTask.objects.create(
            name = f"garbage_{instance.id}",
            task = "project.tasks.garbage",
            clocked = schedule_now,
            one_off = True,
            kwargs = json.dumps({
                'project_folder': fs.path_project(instance.project), 
                'project_tarbal': fs.garbage_project(instance.project),
                'report_prepare_folder': fs.path_report_prepare(instance.project),
            })
        )


@receiver(pre_delete, sender = UserProjectBinding)
def assert_not_shared(sender, instance, **kwargs):
    from ..models import ProjectContainerBinding
    for pcb in ProjectContainerBinding.objects.filter(project = instance.project, container__user = instance.user):
        pcb.container.mark_restart(f"Revoked access to project {instance.project.name}")
        pcb.delete()

