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
            entry.uidNumber.value
        )
        gid = int(
            entry.gidNumber.value
        )

        if (
            profile.uid_number is not None
            and profile.uid_number != uid
        ):
            raise UserDirectoryError(
                f"Profile UID "
                f"{profile.uid_number} does not "
                f"match LDAP UID {uid} for "
                f"{user.username!r}."
            )
    
        if (
            profile.gid_number is not None
            and profile.gid_number != gid
        ):
            raise UserDirectoryError(
                f"Profile GID "
                f"{profile.gid_number} does not "
                f"match LDAP GID {gid} for "
                f"{user.username!r}."
            )
    
        update_fields = []
    
        if profile.uid_number is None:
            profile.uid_number = uid
            update_fields.append(
                "uid_number"
            )
    
        if profile.gid_number is None:
            profile.gid_number = gid
            update_fields.append(
                "gid_number"
            )
    
        if update_fields:
            profile.save(
                update_fields=update_fields
            )
    
        return profile

    if not HUB_SETTINGS.ldap.manage_users:
        raise UserDirectoryError(
            f"LDAP user {user.username!r} "
            "does not exist and LDAP user "
            "provisioning is disabled."
        )

    uid = profile.uid_number
    
    if uid is None:
        uid = (
            HUB_SETTINGS.ldap.user_uid_offset
            + user.pk
        )
    
    gid = profile.gid_number
    
    if gid is None:
        gid = (
            HUB_SETTINGS.ldap.user_gid_number
        )
    
    profile.uid_number = uid
    profile.gid_number = gid

    profile.save(
        update_fields=[
            "uid_number",
            "gid_number",
        ]
    )

    ldap.add_user(
        user=user,
        uid_number=uid,
        gid_number=gid,
    )

    return profile


