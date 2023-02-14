import datetime
import logging
import json

from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db import transaction
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete

from django_celery_beat.models import ClockedSchedule, PeriodicTask
from kooplexhub.settings import KOOPLEX
from hub.models import Group, UserGroupBinding
from education.models import Course, UserCourseBinding, UserAssignmentBinding
from education.filesystem import *

logger = logging.getLogger(__name__)

@receiver(pre_save, sender = Course)
def create_course(sender, instance, **kwargs):
    with transaction.atomic():
        group, _ = Group.objects.select_for_update().get_or_create(name = instance.cleanname, grouptype = Group.TP_COURSE) 
    now = datetime.datetime.now()
    schedule_now = ClockedSchedule.objects.create(clocked_time = now)
    folders = [ f(instance) for f in [ course_public, course_assignment_prepare_root, course_assignment_snapshot, course_workdir_root, course_assignment_root, assignment_correct_root ] ]
    PeriodicTask.objects.create(
        name = f"create_course_{instance.cleanname}_{now}",
        task = "kooplexhub.tasks.create_folders",
        clocked = schedule_now,
        one_off = True,
        kwargs = json.dumps({
            'folders': folders,
            'grant_groupaccess': { group.id: [ 
                (course_public(instance), { 'recursive': True, 'readonly': True }),
                (course_assignment_root(instance), { 'recursive': False, 'readonly': True, 'follow': False }), 
                (course_assignment_root(instance), { 'recursive': False, 'readonly': True, 'follow': True }), 
                ] },
        })
    )


@receiver(pre_delete, sender = Course)
def delete_course(sender, instance, **kwargs):
    try:
        Group.objects.get(name = instance.cleanname, grouptype = Group.TP_COURSE).delete()
    except Group.DoesNotExist:
        pass
    now = datetime.datetime.now()
    schedule_now = ClockedSchedule.objects.create(clocked_time = now)
    folders = [ f(instance) for f in [ course_workdir_root, course_assignment_root, assignment_correct_root, course_root ] ]
    PeriodicTask.objects.create(
        name = f"delete_course_{instance.cleanname}_{now}",
        task = "kooplexhub.tasks.delete_folders",
        clocked = schedule_now,
        one_off = True,
        kwargs = json.dumps({
            'folders': folders,
        })
    )


@receiver(pre_save, sender = UserCourseBinding)
def add_usercourse(sender, instance, **kwargs):
    course = instance.course
    user = instance.user
    group = Group.objects.get(name = course.cleanname, grouptype = Group.TP_COURSE)
    UserGroupBinding.objects.get_or_create(user = user, group = group)
    now = datetime.datetime.now()
    folder_wd = course_workdir(instance)
    folders = [ folder_wd ]
    user_acl = [ (folder_wd, { 'recursive': False, 'readonly': False }) ]
    group_acl = []
    if instance.is_teacher:
        user_acl.extend([ (f(instance.course), { 'readonly': False, 'recursive': True }) for f in [ course_public, course_assignment_prepare_root ] ])
        user_acl.extend([ (assignment_correct_root(instance.course), { 'readonly': False, 'recursive': False, 'follow': True }) ])  #TODO: existing subfolders not handled
    schedule_now = ClockedSchedule.objects.create(clocked_time = now)
    PeriodicTask.objects.create(
        name = f"course_folders_{instance.course.cleanname}-{instance.user}-{now}",
        task = "kooplexhub.tasks.create_folders",
        clocked = schedule_now,
        one_off = True,
        kwargs = json.dumps({
            'folders': folders,
            'grant_useraccess': { instance.user.id: user_acl },
            'grant_groupaccess': { group.id: group_acl },
        })
    )


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
    schedule_now = ClockedSchedule.objects.create(clocked_time = datetime.datetime.now())
    folders = [ f(instance.course) for f in [ course_public, course_assignment_prepare_root, assignment_correct_root ] ]
    PeriodicTask.objects.create(
        name = f"delete_folder_{instance.id}",
        task = "kooplexhub.tasks.delete_folders",
        clocked = schedule_now,
        one_off = True,
        kwargs = json.dumps({
            'folders': [ assignment_workdir_root(instance) ],
            'archives': { course_workdir_garbage(instance): course_workdir(instance) },
            'revoke_useraccess': { instance.user.id: folders }
        })
    )


