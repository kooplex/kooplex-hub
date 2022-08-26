import json
import datetime

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

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
