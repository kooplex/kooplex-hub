
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from education.models import Assignment, UserAssignmentBinding
from education.fs import *

from hub.tasks import delete_folder

@receiver(pre_delete, sender = UserAssignmentBinding)
def delete_userassignment(sender, instance, **kwargs):
    for folder in [assignment_correct_dir(instance), assignment_workdir(instance)]:
        if folder:
            delete_folder( folder )



