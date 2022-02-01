import logging
import json

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete

from kooplexhub.settings import KOOPLEX
from hub.lib import filename, dirname
from hub.models import FilesystemTask, Group, UserGroupBinding
from ..models import Course, UserCourseBinding, UserAssignmentBinding

logger = logging.getLogger(__name__)

code = lambda x: json.dumps([ i.id for i in x ])


@receiver(pre_save, sender = Course)
def create_course(sender, instance, **kwargs):
    with transaction.atomic():
        group, _ = Group.objects.select_for_update().get_or_create(name = instance.cleanname, grouptype = Group.TP_COURSE) 
    FilesystemTask.objects.create(
        folder = dirname.course_public(instance),
        groups_ro = code([group]),
        create_folder = True,
        task = FilesystemTask.TSK_GRANT
    )
    FilesystemTask.objects.create(
        folder = dirname.course_assignment_prepare_root(instance),
        create_folder = True,
        task = FilesystemTask.TSK_CREATE
    )
    FilesystemTask.objects.create(
        folder = dirname.course_assignment_snapshot(instance),
        create_folder = True,
        task = FilesystemTask.TSK_CREATE
    )
    FilesystemTask.objects.create(
        folder = dirname.course_workdir_root(instance),
        create_folder = True,
        task = FilesystemTask.TSK_CREATE
    )
    FilesystemTask.objects.create(
        folder = dirname.course_assignment_root(instance),
        create_folder = True,
        task = FilesystemTask.TSK_CREATE
    )
    FilesystemTask.objects.create(
        folder = dirname.assignment_correct_root(instance),
        create_folder = True,
        task = FilesystemTask.TSK_CREATE
    )


@receiver(pre_delete, sender = Course)
def delete_course(sender, instance, **kwargs):
    try:
        Group.objects.get(name = instance.cleanname, grouptype = Group.TP_COURSE).delete()
    except Group.DoesNotExist:
        pass
#FIXME: archive?
    FilesystemTask.objects.create(
        folder = dirname.course_assignment_root(instance),
        remove_folder = True,
        task = FilesystemTask.TSK_REMOVE
    )
    FilesystemTask.objects.create(
        folder = dirname.course_workdir_root(instance),
        remove_folder = True,
        task = FilesystemTask.TSK_REMOVE
    )
    FilesystemTask.objects.create(
        folder = dirname.assignment_correct_root(instance),
        remove_folder = True,
        task = FilesystemTask.TSK_REMOVE
    )
    FilesystemTask.objects.create(
        folder = dirname.course_root(instance),
        remove_folder = True,
        task = FilesystemTask.TSK_REMOVE
    )


@receiver(pre_save, sender = UserCourseBinding)
def add_usercourse(sender, instance, **kwargs):
    course = instance.course
    user = instance.user
    group = Group.objects.get(name = course.cleanname, grouptype = Group.TP_COURSE)
    UserGroupBinding.objects.get_or_create(user = user, group = group)
    FilesystemTask.objects.create(
        folder = dirname.course_workdir(instance),
        users_rw = code([instance.user]),
        create_folder = True,
        task = FilesystemTask.TSK_GRANT
    )
    if instance.is_teacher:
        FilesystemTask.objects.create(
            folder = dirname.course_public(course),
            users_rw = code([user]),
            task = FilesystemTask.TSK_GRANT
        )
        FilesystemTask.objects.create(
            folder = dirname.course_assignment_prepare_root(course),
            users_rw = code([user]),
            task = FilesystemTask.TSK_GRANT
        )
        FilesystemTask.objects.create(
            folder = dirname.assignment_correct_root(course),
            users_rw = code([user]),
            task = FilesystemTask.TSK_GRANT
        )
        for studentbinding in instance.course.studentbindings:
            FilesystemTask.objects.create(
                folder = dirname.assignment_workdir_root(studentbinding),
                users_ro = code([user]),
                task = FilesystemTask.TSK_GRANT
            )
            FilesystemTask.objects.create(
                folder = dirname.course_public(course),
                users_rw = code([user]),
                task = FilesystemTask.TSK_GRANT
            )
            FilesystemTask.objects.create(
                folder = dirname.course_assignment_prepare_root(course),
                users_rw = code([user]),
                task = FilesystemTask.TSK_GRANT
            )
    else:
        dir_assignment_workdir = dirname.assignment_workdir_root(instance)
        FilesystemTask.objects.create(
            folder = dir_assignment_workdir,
            users_ro = code([instance.user]),
            create_folder = True,
            task = FilesystemTask.TSK_GRANT
        )
        FilesystemTask.objects.create(
            folder = dir_assignment_workdir,
            users_ro = code([teacherbinding.user for teacherbinding in instance.course.teacherbindings]),
            task = FilesystemTask.TSK_GRANT
        )
#FIXME: check feedback folder


@receiver(pre_delete, sender = UserCourseBinding)
def delete_usercourse(sender, instance, **kwargs):
    course = instance.course
    user = instance.user
    try:
        group = Group.objects.get(name = course.cleanname, grouptype = Group.TP_COURSE)
        UserGroupBinding.objects.get(user = user, group = group).delete()
    except UserGroupBinding.DoesNotExist:
        pass
    UserAssignmentBinding.objects.filter(user = user, assignment__course = course).delete()
    if instance.is_teacher:
        FilesystemTask.objects.create(
            folder = dirname.course_public(course),
            users_rw = code([user]),
            task = FilesystemTask.TSK_REVOKE
        )
        FilesystemTask.objects.create(
            folder = dirname.course_assignment_prepare_root(course),
            users_rw = code([user]),
            task = FilesystemTask.TSK_REVOKE
        )
        FilesystemTask.objects.create(
            folder = dirname.assignment_correct_root(course),
            users_rw = code([user]),
            task = FilesystemTask.TSK_REVOKE
        )
    FilesystemTask.objects.create(
        folder = dirname.assignment_workdir_root(instance),
        remove_folder = True,
        task = FilesystemTask.TSK_REMOVE
    )
    FilesystemTask.objects.create(
        folder = dirname.course_workdir(instance),
        tarbal = filename.course_workdir_garbage(instance),
        remove_folder = True,
        task = FilesystemTask.TSK_TAR
    )


