import json
import datetime

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from education.models import Assignment, UserAssignmentBinding
from education.filesystem import *

from django_celery_beat.models import ClockedSchedule, PeriodicTask


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
