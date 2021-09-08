from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

from ..models import Assignment, UserAssignmentBinding

@receiver(post_save, sender = Assignment)
def snapshot_assignment(sender, instance, created, **kwargs):
    from kooplexhub.lib.filesystem import snapshot_assignment
    if created:
        snapshot_assignment(instance)


#FIXME: @receiver(pre_delete, sender = Assignment)
#FIXME: def garbage_assignmentsnapshot(sender, instance, **kwargs):
#FIXME:     from kooplex.lib.filesystem import garbage_assignmentsnapshot
#FIXME:     garbage_assignmentsnapshot(instance)
#FIXME: 
#FIXME: 
#FIXME: @receiver(post_save, sender = UserCourseBinding)
#FIXME: def add_userassignmentbinding(sender, instance, created, **kwargs):
#FIXME:     if created and not instance.is_teacher:
#FIXME:         for a in instance.assignments:
#FIXME:             if a.state == a.ST_VALID:
#FIXME:                 UserAssignmentBinding.objects.create(user = instance.user, assignment = a, expires_at = a.expires_at)


@receiver(post_save, sender = UserAssignmentBinding)
def copy_userassignment(sender, instance, created, **kwargs):
    from kooplexhub.lib.filesystem import cp_assignmentsnapshot, snapshot_userassignment, cp_userassignment2correct, cp_userassignment_feedback
    if created:
        cp_assignmentsnapshot(instance)
    elif instance.state in [ UserAssignmentBinding.ST_SUBMITTED, UserAssignmentBinding.ST_COLLECTED ]:
        snapshot_userassignment(instance)
    elif instance.state == UserAssignmentBinding.ST_CORRECTED:
        cp_userassignment2correct(instance)
    elif instance.state == UserAssignmentBinding.ST_READY:
        cp_userassignment_feedback(instance)


@receiver(pre_delete, sender = UserAssignmentBinding)
def delete_userassignment(sender, instance, **kwargs):
    from kooplexhub.lib.filesystem import delete_userassignment
    delete_userassignment(instance)
