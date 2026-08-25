import logging

from django.db import transaction

from hub.conf import HUB_SETTINGS
from hub.lib.ldap import Ldap, LdapException
from hub.models import Group, UserGroupBinding


logger = logging.getLogger(__name__)


class GroupProvisioningError(Exception):
    pass


def _ldap_enabled():
    return HUB_SETTINGS.ldap.manage_group


def _next_group_id(grouptype):
    """
    Preserve the existing gid allocation semantics, but make them explicit.
    """
    offset = HUB_SETTINGS.ldap.offsets[grouptype]

    latest = (
        Group.objects
        .filter(grouptype=grouptype)
        .order_by("-groupid")
        .values_list("groupid", flat=True)
        .first()
    )

    if latest is None:
        return offset

    return max(latest + 1, offset)


def ensure_group_in_directory(group):
    """
    Ensure the LDAP posixGroup corresponding to an existing
    Django Group exists.

    Django's name/groupid are authoritative here.
    """
    if not HUB_SETTINGS.ldap.manage_group:
        return group

    ldap = Ldap()

    try:
        ldap.get_group(group)
    except LdapException:
        ldap.add_group(group)

    return group


@transaction.atomic
def ensure_group(*, name, grouptype):
    """
    Return a DB Group and ensure its LDAP counterpart exists.

    This replaces Group.pre_save.
    """

    group = (
        Group.objects
        .select_for_update()
        .filter(name=name)
        .first()
    )

    if group is None:
        group = Group.objects.create(
            name=name,
            grouptype=grouptype,
            groupid=_next_group_id(grouptype),
        )

    elif group.grouptype != grouptype:
        raise GroupProvisioningError(
            f"Group {name!r} already exists with "
            f"type {group.grouptype!r}, expected {grouptype!r}."
        )

    ensure_group_in_directory(group)

    return group


@transaction.atomic
def add_user_to_group(*, user, group):
    """
    Ensure both the DB UserGroupBinding and LDAP membership exist.

    Replaces UserGroupBinding.pre_save.
    """

    binding, created = (
        UserGroupBinding.objects.get_or_create(
            user=user,
            group=group,
        )
    )

    if created and _ldap_enabled():
        try:
            Ldap().add_user_to_group(user, group)
        except Exception as exc:
            # Raising here rolls back the DB binding.
            raise GroupProvisioningError(
                f"Could not add {user.username} "
                f"to LDAP group {group.name}"
            ) from exc

    return binding


@transaction.atomic
def remove_user_from_group(*, user, group):
    binding = (
        UserGroupBinding.objects
        .filter(
            user=user,
            group=group,
        )
        .first()
    )

    if binding is None:
        return False

    if _ldap_enabled():
        try:
            Ldap().remove_user_from_group(user, group)
        except LdapException as exc:
            # Depending on LDAP behaviour you may want to tolerate
            # "member not present" here.
            logger.warning(
                "Could not remove %s from LDAP group %s: %s",
                user,
                group,
                exc,
            )

    binding.delete()
    return True



