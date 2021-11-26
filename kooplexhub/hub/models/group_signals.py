import logging

from django.db import models
from django.db.models.signals import pre_save, pre_delete
from django.dispatch import receiver

from ..models import Group

from kooplexhub.settings import KOOPLEX

logger = logging.getLogger(__name__)

@receiver(pre_save, sender = Group)
def ldap_create_group(sender, instance, **kwargs):
    from hub.lib.ldap import Ldap, LdapException
    ldapconf = KOOPLEX.get('ldap', {})
    if ldapconf.get('managegroup') is not True:
        return
    #offset = KOOPLEX.get('ldap', {}).get('offset', {})
    try:
        r = Ldap().get_group(instance)
        logger.warning("Group {} found in ldap {}".format(instance, r)) #ASSERT GID
        return
    except LdapException:
        pass
    try:
        #FIXME: check offset
        Ldap().addgroup(instance)
        logger.info("+ Group {} created in ldap".format(instance))
    except Exception as e:
        logger.error("! Group {} not created in ldap -- {}".format(instance, e))
        return False

@receiver(pre_delete, sender = Group)
def ldap_remove_group(sender, instance, **kwargs):
    from hub.lib.ldap import Ldap
    if KOOPLEX.get('ldap', {}).get('managegroup') is not True:
        return
    try:
        Ldap().removegroup(instance)
        logger.info("- Group {} removed from ldap".format(instance))
    except Exception as e:
        logger.error("! Cannot delete group {} from ldap -- {}".format(instance, e))
        return False

