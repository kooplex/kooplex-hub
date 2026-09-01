from ..conf import HUB_SETTINGS
from ..lib.ldap import (
    Ldap,
    LdapException,
)


class UserDirectoryError(RuntimeError):
    pass


def ensure_user_directory_identity(
    *,
    profile,
):
    user = profile.user

    ldap = Ldap()

    try:
        entry = ldap.get_user(user)

    except LdapException:
        entry = None

    if entry is not None:
        uid = int(
            entry["attributes"]["uidNumber"]
        )

        gid = int(
            entry["attributes"]["gidNumber"]
        )

        profile.uid_number = uid
        profile.gid_number = gid

        profile.save(
            update_fields=[
                "uid_number",
                "gid_number",
            ]
        )

        return profile

    if not HUB_SETTINGS.ldap.manage_users:
        raise UserDirectoryError(
            f"LDAP user {user.username!r} "
            "does not exist and LDAP user "
            "provisioning is disabled."
        )

    profile.uid_number = (
        HUB_SETTINGS.ldap.user_uid_offset
        + user.pk
    )

    profile.gid_number = (
        HUB_SETTINGS.ldap.user_gid_number
    )

    profile.save(
        update_fields=[
            "uid_number",
            "gid_number",
        ]
    )

    ldap.add_user(
        user=user,
        uid_number=profile.uid_number,
        gid_number=profile.gid_number,
    )

    return profile


