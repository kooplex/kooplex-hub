from dataclasses import dataclass, field

from django.contrib.auth import get_user_model

from ..lib.ldap import Ldap
from ..models import Group, UserGroupBinding
from .groups import ensure_group_in_directory

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


@dataclass(frozen=True, slots=True)
class DirectoryDiff:
    missing_users: tuple[str, ...] = ()
    ldap_only_users: tuple[str, ...] = ()

    missing_groups: tuple[str, ...] = ()
    ldap_only_groups: tuple[str, ...] = ()

    gid_mismatches: tuple = ()

    missing_memberships: tuple = ()
    ldap_only_memberships: tuple = ()

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
        ))


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
class RepairResult:
    groups_created: tuple[str, ...] = ()
    memberships_created: tuple[
        MembershipDifference, ...
    ] = ()

    users_skipped: tuple[str, ...] = ()

    groups_deleted: tuple[str, ...] = ()
    users_deleted: tuple[str, ...] = ()



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
        )

