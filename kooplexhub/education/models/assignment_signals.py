
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from education.models import Assignment, UserAssignmentBinding
from education.filesystem import *

from hub.models import Task

@receiver(pre_delete, sender = UserAssignmentBinding)
def delete_userassignment(sender, instance, **kwargs):
    folders = [ assignment_correct_dir(instance) ]
    kwargs = { 
        'folders': [ assignment_correct_dir(instance), userassignment_dir(instance) ] 
    } if instance.assignment.remove_collected else {
        'folders': [ assignment_correct_dir(instance) ],
        'archives': { assignment_garbage(instance): userassignment_dir(instance) },

    }
    Task(
        create = True,
        name = f"garbage assignment {instance.user.username} {instance.assignment.name} {instance.id}",
        task = "kooplexhub.tasks.delete_folders",
        kwargs = kwargs
    )


@receiver(pre_delete, sender = Assignment)
def assignment_tasks_cleanup(sender, instance, **kwargs):
    for a in [ 'task_snapshot', 'task_handout', 'task_collect' ]:
        task = getattr(instance, a)
        if task:
            if task.clocked:
                task.clocked.delete()
            else:
                task.delete()


@receiver(pre_delete, sender = UserAssignmentBinding)
def userassignment_tasks_cleanup(sender, instance, **kwargs):
    for a in [ 'task_handout', 'task_collect' ]: #, 'task_finalize' ]:
        task = getattr(instance, a)
        if task:
            if task.clocked:
                task.clocked.delete()
            else:
                task.delete()
