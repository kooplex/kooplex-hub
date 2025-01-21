
from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from education.models import Assignment, UserAssignmentBinding
from education.filesystem import *

from hub.tasks import delete_folder

@receiver(pre_delete, sender = UserAssignmentBinding)
def delete_userassignment(sender, instance, **kwargs):
    delete_folder( assignment_correct_dir(instance) )
    delete_folder( userassignment_dir(instance) )



