import json
import logging

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from kooplexhub.lib.libbase import standardize_str
from hub.models import FilesystemTask
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
    if instance.id is None and instance.role == UserProjectBinding.RL_CREATOR:
        cleanname = standardize_str(p.name)
        if p.subpath is None:
            p.subpath = f'{cleanname}-{instance.user.username}'
            p.save()
        FilesystemTask.objects.create(
            folder = fs.path_project(p),
            users_rw = code([instance.user]),
            create_folder = True,
            task = FilesystemTask.TSK_GRANT
        )
        FilesystemTask.objects.create(
            folder = fs.path_report_prepare(p),
            users_rw = code([instance.user]),
            create_folder = True,
            task = FilesystemTask.TSK_GRANT
        )
    else:
        raise NotImplementedError
    # group bejegyzes
       
        #_grantgroupaccess(project.groupid, dir_project, acl = 'rwaDxtcy')
        #_grantgroupaccess(project.groupid, dir_reportprepare, acl = 'rwaDxtcy')


@receiver(pre_delete, sender = UserProjectBinding)
def revokeaccess_project(sender, instance, **kwargs):
    if instance.role != UserProjectBinding.RL_CREATOR:
        FilesystemTask.objects.create(
            folder = fs.path_project(instance.project),
            users_rw = code([instance.user]),
            task = FilesystemTask.TSK_REVOKE
        )
        FilesystemTask.objects.create(
            folder = fs.path_report_prepare(instance.project),
            users_rw = code([instance.user]),
            task = FilesystemTask.TSK_REVOKE
        )


@receiver(pre_delete, sender = UserProjectBinding)
def garbagedir_project(sender, instance, **kwargs):
    if instance.role == UserProjectBinding.RL_CREATOR:
        FilesystemTask.objects.create(
            folder = fs.path_project(instance.project),
            tarbal = fs.garbage_project(instance.project),
            remove_folder = True,
            task = FilesystemTask.TSK_TAR
        )
        FilesystemTask.objects.create(
            folder = fs.path_report_prepare(instance.project),
            remove_folder = True,
            task = FilesystemTask.TSK_REMOVE
        )


@receiver(pre_delete, sender = UserProjectBinding)
def assert_not_shared(sender, instance, **kwargs):
    from ..models import ProjectContainerBinding
    for pcb in ProjectContainerBinding.objects.filter(project = instance.project, container__user = instance.user):
        pcb.container.mark_restart(f"Revoked access to project {instance.project.name}")
        pcb.delete()

