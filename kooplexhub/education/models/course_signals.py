import logging

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete

from kooplexhub.settings import KOOPLEX
from hub.models import Group, UserGroupBinding, Task
from education.models import Course, UserCourseBinding, UserAssignmentBinding
from education.filesystem import *

from hub.lib.filesystem import _mkdir
from hub.lib import grantaccess_group

logger = logging.getLogger(__name__)

@receiver(pre_save, sender = Course)
def create_course(sender, instance, **kwargs):
    if instance.id:
        return
    group_students, created = Group.objects.get_or_create(name = instance.folder, grouptype = Group.TP_COURSE) 
    if created:
        logger.error(f'student group {group_students.name} already present')
    group_teachers, created = Group.objects.get_or_create(name = f't-{instance.folder}', grouptype = Group.TP_COURSE) 
    if created:
        logger.error(f'teacher group {group_teachers.name} already present')
    instance.group_students = group_students
    instance.group_teachers = group_teachers

    f_public = course_public(instance)
    _mkdir(f_public)
    grantaccess_group(group_students, f_public, readonly = True)
    grantaccess_group(group_students, f_public, readonly = True, follow = True)
    grantaccess_group(group_teachers, f_public, readonly = False)
    grantaccess_group(group_teachers, f_public, readonly = False, follow = True)

    f_prepare = course_assignment_prepare_root(instance)
    _mkdir(f_prepare)
    grantaccess_group(group_teachers, f_prepare, readonly = False)
    grantaccess_group(group_teachers, f_prepare, readonly = False, follow = True)

    _mkdir(course_assignment_snapshot(instance))

    f_assignment = course_assignment_root(instance)
    _mkdir(f_assignment)
    grantaccess_group(group_students, f_assignment, readonly = True)
    grantaccess_group(group_students, f_assignment, readonly = True, follow = True)
    grantaccess_group(group_teachers, f_assignment, readonly = True)
    grantaccess_group(group_teachers, f_assignment, readonly = True, follow = True)

    f_correct = assignment_correct_root(instance)
    _mkdir(f_correct)
    grantaccess_group(group_teachers, f_correct, readonly = True)
    grantaccess_group(group_teachers, f_correct, readonly = True, follow = True)



@receiver(pre_delete, sender = Course)
def delete_course(sender, instance, **kwargs):
    if instance.group_students:
        instance.group_students.delete()
    if instance.group_teachers:
        instance.group_teachers.delete()
    Task(
        create = True,
        name = f"Delete course {instance.name} ({instance.folder})",
        task = "kooplexhub.tasks.delete_folders",
        kwargs = {
            'folders': [ f(instance) for f in [ course_workdir_root, course_assignment_root, assignment_correct_root, course_root ] ],
        }
    )
    #FIXME: what if garbage is still running!?


@receiver(pre_save, sender = UserCourseBinding)
def add_usercourse(sender, instance, **kwargs):
    course = instance.course
    user = instance.user
    group = instance.course.group_teachers if instance.is_teacher else instance.course.group_students
    UserGroupBinding.objects.get_or_create(user = user, group = group)


@receiver(pre_delete, sender = UserCourseBinding)
def delete_usercourse(sender, instance, **kwargs):
    course = instance.course
    user = instance.user
    try:
        group = instance.course.group_teachers if instance.is_teacher else instance.course.group_students
        UserGroupBinding.objects.get(user = user, group = group).delete()
    except UserGroupBinding.DoesNotExist:
        pass
    #FIXME: below
    UserAssignmentBinding.objects.filter(user = user, assignment__course = course).delete()
    folders = [ f(instance.course) for f in [ course_public, course_assignment_prepare_root, assignment_correct_root ] ]
    Task(
        create = True,
        name = f"Delete user {instance.user.username} from course {instance.course.name}",
        task = "kooplexhub.tasks.delete_folders",
        kwargs = {
            'folders': [ assignment_workdir_root(instance) ],
            'archives': { course_workdir_garbage(instance): course_workdir(instance) },
            'revoke_useraccess': { instance.user.id: folders }
        }
    )


