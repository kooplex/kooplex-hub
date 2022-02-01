import logging

from django.db import models
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver

from ..models import Group, UserGroupBinding

from kooplexhub.settings import KOOPLEX

logger = logging.getLogger(__name__)

@receiver(pre_save, sender = Group)
def ldap_create_group(sender, instance, **kwargs):
    from hub.lib.ldap import Ldap, LdapException
    ldapconf = KOOPLEX.get('ldap', {})
    if not ldapconf.get('managegroup', False):
        logger.debug('skip ldap update')
        return
    try:
        r = Ldap().get_group(instance)
        logger.warning("Group {} found in ldap {}".format(instance, r))
        instance.groupid = r['attributes']['gidNumber']
        logger.info("+ Group {} found in ldap".format(instance))
        return
    except LdapException:
        pass
    try:
        gids = [ g.groupid for g in Group.objects.filter(grouptype = instance.grouptype) ]
        gids.append( KOOPLEX.get('ldap', {}).get('offset', {}).get(instance.grouptype, 1000) )
        instance.groupid = max(gids) if len(gids) == 1 else max(gids) + 1
        Ldap().addgroup(instance)
        logger.info("+ Group {} created in ldap".format(instance))
    except Exception as e:
        logger.error("! Group {} not created in ldap -- {}".format(instance, e))
        return False


@receiver(pre_delete, sender = Group)
def ldap_remove_group(sender, instance, **kwargs):
    from hub.lib.ldap import Ldap
    if not KOOPLEX.get('ldap', {}).get('managegroup', False):
        logger.debug('skip ldap update')
        return
    try:
        Ldap().removegroup(instance)
        logger.info("- Group {} removed from ldap".format(instance))
    except Exception as e:
        logger.error("! Cannot delete group {} from ldap -- {}".format(instance, e))
        return False


@receiver(pre_save, sender = UserGroupBinding)
def ldap_groupadd(sender, instance, **kwargs):
    from hub.lib.ldap import Ldap
    if not KOOPLEX.get('ldap', {}).get('managegroup', False):
        logger.debug('skip ldap update')
        return
    try:
        Ldap().addusertogroup(instance.user, instance.group)
        logger.info("+ User {} added to group {} in ldap".format(instance.user, instance.group))
    except Exception as e:
        logger.error("! Cannot add user {} to group {} in ldap -- {}".format(instance.user, instance.group, e))
        return False


@receiver(pre_delete, sender = UserGroupBinding)
def ldap_groupdel(sender, instance, **kwargs):
    from hub.lib.ldap import Ldap
    if not KOOPLEX.get('ldap', {}).get('managegroup', False):
        logger.debug('skip ldap update')
        return
    try:
        Ldap().removeuserfromgroup(instance.user, instance.group)
        logger.info("- User {} removed from group {} in ldap".format(instance.user, instance.group))
    except Exception as e:
        logger.error("! Cannot remove user {} from group {} in ldap -- {}".format(instance.user, instance.group, e))
        return False

