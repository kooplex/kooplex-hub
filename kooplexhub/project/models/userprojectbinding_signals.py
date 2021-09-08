import logging

from django.db.models.signals import pre_save, post_save, pre_delete, post_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)

from ..models import UserProjectBinding

@receiver(pre_save, sender = UserProjectBinding)
def assert_single_creator(sender, instance, **kwargs):
    p = instance.project
    try:
        upb = UserProjectBinding.objects.get(project = p, role = UserProjectBinding.RL_CREATOR)
        if instance.role == UserProjectBinding.RL_CREATOR:
            assert upb.id == instance.id, "Project %s cannot have more than one creator" % p
    except UserProjectBinding.DoesNotExist:
        assert instance.role == UserProjectBinding.RL_CREATOR, "The first user project binding must be the creator %s" % instance


@receiver(post_save, sender = UserProjectBinding)
def mkdir_project(sender, instance, created, **kwargs):
    from kooplexhub.lib import mkdir_project
    if instance.role == UserProjectBinding.RL_CREATOR:
        mkdir_project(instance.project)


#FIXME:   #FIXME: ezekre elvben nincs szukseg, ha majd a group rendben megy
@receiver(post_save, sender = UserProjectBinding)
def grantaccess_project(sender, instance, created, **kwargs):
    from kooplexhub.lib import grantaccess_project
    if created and instance.role != UserProjectBinding.RL_CREATOR:
        grantaccess_project(instance)


#FIXME:   @receiver(post_save, sender = UserProjectBinding)
#FIXME:   def grantaccess_report(sender, instance, created, **kwargs):
#FIXME:       from kooplex.lib.filesystem import grantaccess_report
#FIXME:       if created:
#FIXME:           for report in instance.project.reports:
#FIXME:               grantaccess_report(report, instance.user)


@receiver(pre_delete, sender = UserProjectBinding)
def revokeaccess_project(sender, instance, **kwargs):
    from kooplexhub.lib import revokeaccess_project
    revokeaccess_project(instance)


@receiver(pre_delete, sender = UserProjectBinding)
def garbagedir_project(sender, instance, **kwargs):
    from kooplexhub.lib import garbagedir_project
    if instance.role == UserProjectBinding.RL_CREATOR:
        garbagedir_project(instance.project)


#FIXME:   @receiver(post_save, sender = UserProjectBinding)
#FIXME:   def revokeaccess_report(sender, instance, **kwargs):
#FIXME:       from kooplex.lib.filesystem import revokeaccess_report
#FIXME:       for report in instance.project.reports:
#FIXME:           revokeaccess_report(report, instance.user)
#FIXME:   

@receiver(pre_delete, sender = UserProjectBinding)
def assert_not_shared(sender, instance, **kwargs):
    from container.models import Container
    from ..models import ProjectContainerBinding
    bindings = UserProjectBinding.objects.filter(project = instance.project)
   #FIXME if instance.role == UserProjectBinding.RL_CREATOR:
   #FIXME     assert len(bindings) == 1, f'Cannot delete creator binding because {len(bindings)} project bindings exists'
    for psb in ProjectContainerBinding.objects.filter(project = instance.project, container__user = instance.user):
        if psb.container.state == Container.ST_RUNNING:
            psb.container.state = Container.ST_NEED_RESTART
            psb.container.save()
        psb.delete()

