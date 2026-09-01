import logging
from dataclasses import dataclass, field

from django.contrib.auth import get_user_model
from django.db import IntegrityError

from ..lib.ldap import Ldap
from ..models import (
    Group,
    Profile,
    UserGroupBinding,
)
from .groups import ensure_group_in_directory

logger = logging.getLogger(__name__)
User = get_user_model()

@dataclass(frozen=True, slots=True)
class LdapUserInfo:
    username: str
    uid_number: int | None
    gid_number: int | None


@dataclass(frozen=True, slots=True)
class LdapGroupInfo:
    name: str
    gid_number: int
    members: frozenset[str]


@dataclass(
    frozen=True,
    slots=True,
)
class ProfileIdentityMissing:
    username: str

    database_uid: int | None
    database_gid: int | None

    ldap_uid: int | None
    ldap_gid: int | None


@dataclass(
    frozen=True,
    slots=True,
)
class ProfileIdentityMismatch:
    username: str

    database_uid: int | None
    ldap_uid: int | None

    database_gid: int | None
    ldap_gid: int | None


@dataclass(
    frozen=True,
    slots=True,
)
class MissingProfile:
    username: str


@dataclass(frozen=True, slots=True)
class GidMismatch:
    group_name: str
    database_gid: int
    ldap_gid: int


@dataclass(frozen=True, slots=True)
class MembershipDifference:
    username: str
    group_name: str


@dataclass(frozen=True, slots=True)
class DirectoryDiff:
    missing_users: tuple[str, ...] = ()
    ldap_only_users: tuple[str, ...] = ()

    missing_groups: tuple[str, ...] = ()
    ldap_only_groups: tuple[str, ...] = ()

    gid_mismatches: tuple = ()

    missing_memberships: tuple = ()
    ldap_only_memberships: tuple = ()

    missing_profiles: tuple[
        MissingProfile,
        ...,
    ] = ()

    profile_identity_missing: tuple[
        ProfileIdentityMissing,
        ...,
    ] = ()

    profile_identity_mismatches: tuple[
        ProfileIdentityMismatch,
        ...,
    ] = ()
    

    @property
    def consistent(self):
        return not any((
            self.missing_users,
            self.ldap_only_users,
            self.missing_groups,
            self.ldap_only_groups,
            self.gid_mismatches,
            self.missing_memberships,
            self.ldap_only_memberships,
            self.missing_profiles,
            self.profile_identity_missing,
            self.profile_identity_mismatches,
        ))


@dataclass(frozen=True, slots=True)
class RepairResult:
    groups_created: tuple[str, ...] = ()
    memberships_created: tuple[
        MembershipDifference, ...
    ] = ()

    users_skipped: tuple[str, ...] = ()

    groups_deleted: tuple[str, ...] = ()
    users_deleted: tuple[str, ...] = ()

    profile_identities_repaired: tuple[
        str,
        ...,
    ] = ()

    profile_identities_skipped: tuple[
        str,
        ...,
    ] = ()



def _entry_value(entry, attribute, default=None):
    value = getattr(entry, attribute, None)

    if value is None:
        return default

    return value.value


def _entry_values(entry, attribute):
    value = getattr(entry, attribute, None)

    if value is None:
        return ()

    return tuple(value.values or ())


class DirectoryReconciler:

    def __init__(self, backend=None):
        self.backend = backend or Ldap()

    def ldap_users(self):
        result = {}

        for entry in self.backend.users():
            username = _entry_value(entry, "uid")

            if not username:
                continue

            uid_number = _entry_value(
                entry,
                "uidNumber",
            )

            gid_number = _entry_value(
                entry,
                "gidNumber",
            )

            result[str(username)] = LdapUserInfo(
                username=str(username),
                uid_number=(
                    int(uid_number)
                    if uid_number is not None
                    else None
                ),
                gid_number=(
                    int(gid_number)
                    if gid_number is not None
                    else None
                ),
            )

        return result


    def ldap_groups(self):
        result = {}

        for entry in self.backend.groups():
            name = _entry_value(entry, "cn")

            if not name:
                continue

            gid = _entry_value(
                entry,
                "gidNumber",
            )

            result[str(name)] = LdapGroupInfo(
                name=str(name),
                gid_number=int(gid),
                members=frozenset(
                    str(username)
                    for username in _entry_values(
                        entry,
                        "memberUid",
                    )
                ),
            )

        return result


    def inspect(self):
        ldap_users = self.ldap_users()
        ldap_groups = self.ldap_groups()

        db_users = {
            user.username: user
            for user in User.objects.filter(
                is_superuser=False
            )
        }

        profiles_by_user_id = {
            profile.user_id: profile
            for profile in (
                Profile.objects
                .filter(
                    user_id__in=[
                        user.pk
                        for user in db_users.values()
                    ]
                )
            )
        }

        missing_profiles = []
        profile_identity_missing = []
        profile_identity_mismatches = []
        
        for username in sorted(
            set(db_users) & set(ldap_users)
        ):
            user = db_users[username]
            ldap_user = ldap_users[username]
        
            profile = profiles_by_user_id.get(
                user.pk
            )
        
            if profile is None:
                missing_profiles.append(
                    MissingProfile(
                        username=username,
                    )
                )
                continue
        
            ldap_uid = ldap_user.uid_number
            ldap_gid = ldap_user.gid_number
        
            #
            # LDAP identity itself is incomplete.
            # Do not manufacture values from DB/config
            # during reconciliation.
            #
            if (
                ldap_uid is None
                or ldap_gid is None
            ):
                profile_identity_mismatches.append(
                    ProfileIdentityMismatch(
                        username=username,
                        database_uid=(
                            profile.uid_number
                        ),
                        ldap_uid=ldap_uid,
                        database_gid=(
                            profile.gid_number
                        ),
                        ldap_gid=ldap_gid,
                    )
                )
                continue
        
            missing_uid = (
                profile.uid_number is None
            )
        
            missing_gid = (
                profile.gid_number is None
            )
        
            if missing_uid or missing_gid:
                #
                # A non-null side may still already
                # conflict with LDAP. That is NOT a
                # safe fill.
                #
                conflicting_uid = (
                    profile.uid_number is not None
                    and profile.uid_number
                    != ldap_uid
                )
        
                conflicting_gid = (
                    profile.gid_number is not None
                    and profile.gid_number
                    != ldap_gid
                )
        
                if (
                    conflicting_uid
                    or conflicting_gid
                ):
                    profile_identity_mismatches.append(
                        ProfileIdentityMismatch(
                            username=username,
                            database_uid=(
                                profile.uid_number
                            ),
                            ldap_uid=ldap_uid,
                            database_gid=(
                                profile.gid_number
                            ),
                            ldap_gid=ldap_gid,
                        )
                    )
        
                else:
                    profile_identity_missing.append(
                        ProfileIdentityMissing(
                            username=username,
                            database_uid=(
                                profile.uid_number
                            ),
                            database_gid=(
                                profile.gid_number
                            ),
                            ldap_uid=ldap_uid,
                            ldap_gid=ldap_gid,
                        )
                    )
        
                continue
        
            if (
                profile.uid_number != ldap_uid
                or profile.gid_number != ldap_gid
            ):
                profile_identity_mismatches.append(
                    ProfileIdentityMismatch(
                        username=username,
                        database_uid=(
                            profile.uid_number
                        ),
                        ldap_uid=ldap_uid,
                        database_gid=(
                            profile.gid_number
                        ),
                        ldap_gid=ldap_gid,
                    )
                )

        db_groups = {
            group.name: group
            for group in Group.objects.all()
        }

        missing_users = sorted(
            set(db_users) - set(ldap_users)
        )

        ldap_only_users = sorted(
            set(ldap_users) - set(db_users)
        )

        missing_groups = sorted(
            set(db_groups) - set(ldap_groups)
        )

        ldap_only_groups = sorted(
            set(ldap_groups) - set(db_groups)
        )

        gid_mismatches = []

        for name in (
            set(db_groups) & set(ldap_groups)
        ):
            db_group = db_groups[name]
            ldap_group = ldap_groups[name]

            if (
                db_group.groupid
                != ldap_group.gid_number
            ):
                gid_mismatches.append(
                    GidMismatch(
                        group_name=name,
                        database_gid=db_group.groupid,
                        ldap_gid=ldap_group.gid_number,
                    )
                )

        db_memberships = set(
            UserGroupBinding.objects.values_list(
                "user__username",
                "group__name",
            )
        )

        ldap_memberships = {
            (username, group.name)
            for group in ldap_groups.values()
            for username in group.members
        }

        missing_memberships = [
            MembershipDifference(
                username=username,
                group_name=group_name,
            )
            for username, group_name
            in sorted(
                db_memberships - ldap_memberships
            )
        ]

        ldap_only_memberships = [
            MembershipDifference(
                username=username,
                group_name=group_name,
            )
            for username, group_name
            in sorted(
                ldap_memberships - db_memberships
            )
        ]

        return DirectoryDiff(
            missing_users=tuple(missing_users),
            ldap_only_users=tuple(
                ldap_only_users
            ),
            missing_groups=tuple(
                missing_groups
            ),
            ldap_only_groups=tuple(
                ldap_only_groups
            ),
            gid_mismatches=tuple(
                gid_mismatches
            ),
            missing_memberships=tuple(
                missing_memberships
            ),
            ldap_only_memberships=tuple(
                ldap_only_memberships
            ),
            missing_profiles=tuple(
                missing_profiles
            ),
            profile_identity_missing=tuple(
                profile_identity_missing
            ),
            profile_identity_mismatches=tuple(
                profile_identity_mismatches
            ),
        )


    def repair(
        self, 
        diff,
        *,
        delete_ldap_only_groups=False,
        delete_ldap_only_users=False,
    ):
        created_groups = []
        created_memberships = []
        skipped_users = []

        ldap_users = self.ldap_users()

        for group_name in diff.missing_groups:
            group = Group.objects.get(
                name=group_name
            )

            ensure_group_in_directory(group)

            created_groups.append(
                group_name
            )

        for username in diff.missing_users:
            skipped_users.append(username)

        ldap_users = self.ldap_users()
        ldap_groups = self.ldap_groups()

        for item in diff.missing_memberships:

            if item.username not in ldap_users:
                continue

            if item.group_name not in ldap_groups:
                # It may just have been created above.
                ldap_groups = self.ldap_groups()

            if item.group_name not in ldap_groups:
                continue

            user = User.objects.get(
                username=item.username
            )

            group = Group.objects.get(
                name=item.group_name
            )

            self.backend.add_user_to_group(
                user,
                group,
            )

            created_memberships.append(item)

        deleted_groups = []
        deleted_users = []
        
        if delete_ldap_only_groups:
            for group_name in diff.ldap_only_groups:
                self.backend.remove_group_by_name(
                    group_name
                )
                deleted_groups.append(group_name)
        
        if delete_ldap_only_users:
            for username in diff.ldap_only_users:
                self.backend.remove_user_by_username(
                    username
                )
                deleted_users.append(username)

        profile_identities_repaired = []
        profile_identities_skipped = []

        for item in diff.profile_identity_missing:
            user = (
                User.objects
                .filter(
                    username=item.username
                )
                .first()
            )
        
            if user is None:
                profile_identities_skipped.append(
                    item.username
                )
                continue
        
            profile = (
                Profile.objects
                .filter(user=user)
                .first()
            )
        
            if profile is None:
                profile_identities_skipped.append(
                    item.username
                )
                continue
        
            #
            # Re-read LDAP rather than blindly trusting
            # the earlier inspection snapshot.
            #
            ldap_info = (
                self.ldap_users()
                .get(item.username)
            )
        
            if (
                ldap_info is None
                or ldap_info.uid_number is None
                or ldap_info.gid_number is None
            ):
                profile_identities_skipped.append(
                    item.username
                )
                continue
        
            #
            # Only fill missing fields.
            # Never overwrite a populated identity.
            #
            update_fields = []
        
            if profile.uid_number is None:
                profile.uid_number = (
                    ldap_info.uid_number
                )
                update_fields.append(
                    "uid_number"
                )
        
            elif (
                profile.uid_number
                != ldap_info.uid_number
            ):
                profile_identities_skipped.append(
                    item.username
                )
                continue
        
            if profile.gid_number is None:
                profile.gid_number = (
                    ldap_info.gid_number
                )
                update_fields.append(
                    "gid_number"
                )
        
            elif (
                profile.gid_number
                != ldap_info.gid_number
            ):
                profile_identities_skipped.append(
                    item.username
                )
                continue
        
            if not update_fields:
                continue
        
            try:
                profile.save(
                    update_fields=update_fields
                )
            except IntegrityError as error:
                profile_identities_skipped.append(
                    item.username
                )
            
                logger.warning(
                    "Could not reconcile POSIX identity "
                    "for user=%s uid=%s gid=%s: %s",
                    item.username,
                    ldap_info.uid_number,
                    ldap_info.gid_number,
                    error,
                )
            
                continue
        
            profile_identities_repaired.append(
                item.username
            )

        return RepairResult(
            groups_created=tuple(
                created_groups
            ),
            memberships_created=tuple(
                created_memberships
            ),
            users_skipped=tuple(
                skipped_users
            ),
            groups_deleted=tuple(
                deleted_groups
            ),
            users_deleted=tuple(
                deleted_users
            ),
            profile_identities_repaired=tuple(
                profile_identities_repaired
            ),
            profile_identities_skipped=tuple(
                profile_identities_skipped
            ),
        )

