import json
import datetime

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from hub.models import Group
from education.models import Assignment, UserAssignmentBinding
from education.filesystem import *

from django_celery_beat.models import ClockedSchedule, PeriodicTask


@receiver(post_save, sender = Assignment)
def snapshot_assignment(sender, instance, created, **kwargs):
    if created:
        instance.filename = instance.snapshot
        now = datetime.datetime.now()
        schedule_now = ClockedSchedule.objects.create(clocked_time = now)
        instance.task_snapshot = PeriodicTask.objects.create(
            name = f"create_assignment_{instance.id}",
            task = "kooplexhub.tasks.create_tar",
            clocked = schedule_now,
            one_off = True,
            kwargs = json.dumps({
                'folder': assignment_source(instance),
                'tarbal': instance.filename,
            })
        )
        if instance.ts_handout:
            schedule = ClockedSchedule.objects.create(clocked_time = instance.ts_handout)
            instance.task_handout = PeriodicTask.objects.create(
                name = f"handout_{instance.id}",
                task = "education.tasks.assignment_handout",
                clocked = schedule,
                one_off = True,
                kwargs = json.dumps({
                    'assignment_id': instance.id,
                })
            )
        if instance.ts_collect:
            schedule = ClockedSchedule.objects.create(clocked_time = instance.ts_collect)
            instance.task_collect = PeriodicTask.objects.create(
                name = f"collect_{instance.filename}",
                task = "education.tasks.assignment_collect",
                clocked = schedule,
                one_off = True,
                kwargs = json.dumps({
                    'assignment_id': instance.id,
                })
            )
        instance.save()


@receiver(pre_save, sender = UserAssignmentBinding)
def copy_userassignment(sender, instance, **kwargs):
    now = datetime.datetime.now()
    if instance.id is None:
        group = Group.objects.get(name = instance.assignment.course.cleanname, grouptype = Group.TP_COURSE)
        schedule_now = ClockedSchedule.objects.create(clocked_time = now)
        instance.task_handout = PeriodicTask.objects.create(
            name = f"handout_{instance.assignment.folder}_{instance.user.username}-{now}",
            task = "kooplexhub.tasks.extract_tar",
            clocked = schedule_now,
            one_off = True,
            kwargs = json.dumps({
                'folder': assignment_workdir(instance),
                'tarbal': instance.assignment.filename,
                'users_rw': [ instance.user.id ],
                'users_ro': [ teacherbinding.user.id for teacherbinding in instance.assignment.course.teacherbindings ],
                'recursive': True,
            })
        )
    elif instance.state in [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ]:
        if instance.task_collect:
            instance.task_collect.clocked.clocked_time = now
            instance.task_collect.clocked.save()
        else:
            schedule_now = ClockedSchedule.objects.create(clocked_time = now)
            instance.task_collect = PeriodicTask.objects.create(
                name = f"snapshot_{instance.id}",
                task = "kooplexhub.tasks.create_tar",
                clocked = schedule_now,
                one_off = True,
        #FIXME: QUOTA CHECK HANDLE IT
                kwargs = json.dumps({
                    'folder': assignment_workdir(instance),
                    'tarbal': assignment_collection(instance),
                })
            )
    elif instance.state == UserAssignmentBinding.ST_CORRECTED:
        if instance.task_correct:
            instance.task_correct.clocked.clocked_time = now
            instance.task_correct.clocked.save()
        else:
            schedule_now = ClockedSchedule.objects.create(clocked_time = now)
            instance.task_correct = PeriodicTask.objects.create(
                name = f"extract_{instance.id}",
                task = "kooplexhub.tasks.extract_tar",
                clocked = schedule_now,
                one_off = True,
                kwargs = json.dumps({
                    'folder': assignment_correct_dir(instance),
                    'tarbal': assignment_collection(instance),
                    'users_rw': [ b.user.id for b in instance.assignment.course.teacherbindings ],
                })
            )
    elif instance.state == UserAssignmentBinding.ST_READY:
        if instance.task_finalize:
            instance.task_finalize.clocked.clocked_time = now
            instance.task_finalize.clocked.save()
        else:
            schedule_now = ClockedSchedule.objects.create(clocked_time = now)
            instance.task_finalize = PeriodicTask.objects.create(
                name = f"finalize_{instance.id}",
                task = "kooplexhub.tasks.create_tar",
                clocked = schedule_now,
                one_off = True,
        #FIXME: feedback csak student kérésére lesz kicsomagolva
                kwargs = json.dumps({
                    'binding_id': instance.id,
                    'folder': assignment_correct_dir(instance), 
                    'tarbal': assignment_feedback(instance),
                })
            )


@receiver(pre_delete, sender = UserAssignmentBinding)
def delete_userassignment(sender, instance, **kwargs):
    folders = [ assignment_correct_dir(instance) ]
    kwargs = { 
        'folders': [ assignment_correct_dir(instance), userassignment_dir(instance) ] 
    } if instance.assignment.remove_collected else {
        'folders': [ assignment_correct_dir(instance) ],
        'archives': { assignment_garbage(instance): userassignment_dir(instance) },

    }
    schedule_now = ClockedSchedule.objects.create(clocked_time = datetime.datetime.now())
    PeriodicTask.objects.get_or_create(
        name = f"garbage_userassignment_{instance.id}",
        task = "kooplexhub.tasks.delete_folders",
        clocked = schedule_now,
        one_off = True,
        kwargs = json.dumps(kwargs)
    )


@receiver(pre_delete, sender = Assignment)
def assignment_tasks_cleanup(sender, instance, **kwargs):
    for a in [ 'task_snapshot', 'task_handout', 'task_collect' ]:
        task = getattr(instance, a)
        if task:
            task.clocked.delete()


@receiver(pre_delete, sender = UserAssignmentBinding)
def userassignment_tasks_cleanup(sender, instance, **kwargs):
    for a in [ 'task_handout', 'task_collect', 'task_correct', 'task_finalize' ]:
        task = getattr(instance, a)
        if task:
            task.clocked.delete()
