import logging

from django.db import models
from django.db.models.signals import post_save, pre_delete, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

from .project import Project, UserProjectBinding

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class Group(models.Model):
    groupid = models.IntegerField(null = False)
    name = models.CharField(max_length = 32, null = False)
    project = models.ForeignKey(Project, null = True)
    is_active = models.BooleanField(default = True)

    def __str__(self):
        return self.name

class UserGroupBinding(models.Model):
    user = models.ForeignKey(User, null = False)
    group = models.ForeignKey(Group, null = False)


@receiver(post_save, sender = Group)
def ldap_create_group(sender, instance, created, **kwargs):
    from kooplex.lib.ldap import Ldap
    if created:
        logger.info("Group %s registered in ldap" % instance)
        try:
            Ldap().addgroup(instance) #FIXME: check existance
        except Exception as e:
            logger.error("cannot create group %s in ldap -- %s" % (instance, e))

@receiver(post_save, sender = Group)
def ldap_remove_group(sender, instance, **kwargs):
    from kooplex.lib.ldap import Ldap
    if instance.is_active == False:
        try:
            Ldap().removegroup(instance)
            logger.info("Group %s removed from ldap" % instance)
        except Exception as e:
            logger.error("cannot delete group %s from ldap -- %s" % (instance, e))

@receiver(post_delete, sender = Group)
def ldap_remove_group2(sender, instance, **kwargs):
    from kooplex.lib.ldap import Ldap
    try:
        Ldap().removegroup(instance)
        logger.info("Group %s removed from ldap" % instance)
    except Exception as e:
        logger.error("cannot delete group %s from ldap -- %s" % (instance, e))

@receiver(post_save, sender = UserGroupBinding)
def ldap_add_user_to_group(sender, instance, created, **kwargs):
    from kooplex.lib.ldap import Ldap
    if created:
        try:
            Ldap().addusertogroup(instance.user, instance.group)
            logger.info("User %s is registered to group %s in ldap" % (instance.user, instance.group))
        except Exception as e:
            logger.error("cannot add user %s to group %s in ldap -- %s" % (instance.user, instance.group, e))

@receiver(pre_delete, sender = UserGroupBinding)
def ldap_remove_user_from_group(sender, instance, **kwargs):
    from kooplex.lib.ldap import Ldap
    try:
        Ldap().removeuserfromgroup(instance.user, instance.group)
        logger.info("User %s is deregistered from group %s in ldap" % (instance.user, instance.group))
    except Exception as e:
        logger.error("cannot deregister user %s from group %s in ldap -- %s" % (instance.user, instance.group, e))

@receiver(post_save, sender = Project)
def create_group_for_project(sender, instance, created, **kwargs):
    if created:
        logger.debug("%s" % instance)
        try:
            last_gid = Group.objects.all().aggregate(models.Max('groupid'))['groupid__max']
            gid = KOOPLEX.get('min_groupid', 10000) if last_gid is None else last_gid + 1
            logger.debug("gid %d" % gid)
            group = Group.objects.create(name = instance.safename, groupid = gid, project = instance)
            logger.info("created group: %s" % group)
        except Exception as e:
            logger.error("Cannot create new group for project %s -- %s" % (instance, e))

@receiver(pre_delete, sender = Project)
def inactivate_group_for_project(sender, instance, **kwargs):
    logger.debug("%s" % instance)
    try:
        group = Group.objects.get(project = instance)
        group.is_active = False
        group.save()
        logger.info("inactivated group: %s" % group)
    except Group.DoesNotExist:
        logger.error("Cannot find group for project %s" % instance)

@receiver(post_save, sender = UserProjectBinding)
def create_usergroupbinding_for_userprojectbinding(sender, instance, created, **kwargs):
    if created:
        try:
            group = Group.objects.get(name = instance.project.safename)
            binding = UserGroupBinding.objects.create(group = group, user = instance.user)
            logger.debug("new group binding: %s" % binding)
        except Exception as e:
            logger.error("Cannot create binding for %s -- %s" % (instance, e))

@receiver(pre_delete, sender = UserProjectBinding)
def delete_usergroupbinding_for_userprojectbinding(sender, instance, **kwargs):
    try:
        group = Group.objects.get(name = instance.project.safename)
        binding = UserGroupBinding.objects.get(group = group, user = instance.user)
        binding.delete()
        logger.debug("deleted group binding: %s" % binding)
    except Exception as e:
        logger.error("Cannot delete binding for %s -- %s" % (instance, e))

