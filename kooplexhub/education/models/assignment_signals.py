import json

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from hub.models import FilesystemTask, Group
from ..models import Assignment, UserAssignmentBinding
from ..filesystem import *

code = lambda x: json.dumps([ i.id for i in x ])


@receiver(post_save, sender = Assignment)
def snapshot_assignment(sender, instance, created, **kwargs):
    if created:
        instance.filename = instance.snapshot
        FilesystemTask.objects.create(
            folder = assignment_source(instance),
            tarbal = instance.filename,
            task = FilesystemTask.TSK_TAR
        )
        instance.save()


@receiver(pre_save, sender = UserAssignmentBinding)
def copy_userassignment(sender, instance, **kwargs):
    if instance.id is None:
        group = Group.objects.get(name = instance.assignment.course.cleanname, grouptype = Group.TP_COURSE)
        FilesystemTask.objects.create(
            folder = assignment_workdir(instance),
            tarbal = instance.assignment.filename,
            users_rw = code([instance.user]),
            users_ro = code([ teacherbinding.user for teacherbinding in instance.assignment.course.teacherbindings ]),
            recursive = True,
            task = FilesystemTask.TSK_UNTAR
        )
    elif instance.state in [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ]:
        #FIXME: QUOTA!
        FilesystemTask.objects.create(
            folder = assignment_workdir(instance),
            tarbal = assignment_collection(instance),
            task = FilesystemTask.TSK_TAR
        )
    elif instance.state == UserAssignmentBinding.ST_CORRECTED:
        FilesystemTask.objects.create(
            folder = assignment_correct_dir(instance),
            tarbal = assignment_collection(instance),
            task = FilesystemTask.TSK_UNTAR
        )
        for teacherbinding in instance.assignment.course.teacherbindings:
            FilesystemTask.objects.create(
                folder = assignment_correct_dir(instance),
                users_rw = code([ teacherbinding.user ]),
                task = FilesystemTask.TSK_GRANT
            )
    elif instance.state == UserAssignmentBinding.ST_READY:
        FilesystemTask.objects.create(
            folder = assignment_correct_dir(instance),
            tarbal = assignment_feedback(instance),
            task = FilesystemTask.TSK_TAR
        )
    #FIXME: feedback csak student kérésére lesz kicsomagolva
    #
    #    FilesystemTask.objects.create(
    #        folder = dirname.assignment_feedback_dir(instance),
    #        tarbal = filename.assignment_feedback(instance.assignment),
    #        grantee_user = instance.user.profile.userid,
    #        readonly = True
    #        task = FilesystemTask.TSK_UNTAR
    #    )
    #with tarfile.open(archivefile, mode='r') as archive:
    #    archive.extractall(path = dir_target)
    #_chown(dir_target, userassignmentbinding.user.profile.userid, users_gid)




@receiver(pre_delete, sender = UserAssignmentBinding)
def delete_userassignment(sender, instance, **kwargs):
    dir_assignment = userassignment_dir(instance)
    if instance.assignment.remove_collected:
        FilesystemTask.objects.create(
            folder = dir_assignment,
            remove_folder = True,
            task = FilesystemTask.TSK_REMOVE
        )
    else:
        FilesystemTask.objects.create(
            folder = dir_assignment,
            tarbal = assignment_garbage(instance),
            remove_folder = True,
            task = FilesystemTask.TSK_TAR
        )
    #FIXME: archive?
        FilesystemTask.objects.create(
            folder = assignment_correct_dir(instance),
            remove_folder = True,
            task = FilesystemTask.TSK_REMOVE
        )

