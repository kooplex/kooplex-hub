from dataclasses import dataclass
import pwgen

from django.utils import timezone

from hub.conf import HUB_SETTINGS
from hub.lib.ldap import (
    Ldap,
    LdapException,
)
from hub.models import Profile
from hub.services.kubernetes_identity import (
    inspect_user_kubernetes_identity,
    ensure_user_kubernetes_identity,
)
from hub.services.storage import (
    inspect_user_storage,
    ensure_user_storage,
)
from hub.services.users_directory import (
    ensure_user_directory_identity,
)
from hub.services.directory import (
    DirectoryService,
)


@dataclass(
    frozen=True,
    slots=True,
)
class UserDirectoryIdentityStatus:
    present: bool

    ldap_uid: int | None
    ldap_gid: int | None

    uid_matches: bool
    gid_matches: bool

    @property
    def ready(self):
        return (
            self.present
            and self.uid_matches
            and self.gid_matches
        )


@dataclass(
    frozen=True,
    slots=True,
)
class UserReadinessStatus:
    profile_id: int
    username: str

    token_ready: bool

    directory: (
        UserDirectoryIdentityStatus
    )

    storage: object

    kubernetes: tuple

    kubernetes_ready: bool

    @property
    def ready(self):
        return (
            self.token_ready
            and self.directory.ready
            and self.storage.ready
            and self.kubernetes_ready
        )

    @property
    def problems(self):
        result = []

        if not self.token_ready:
            result.append(
                "job token is missing"
            )

        if not self.directory.present:
            result.append(
                "LDAP identity is missing"
            )

        elif not self.directory.uid_matches:
            result.append(
                "LDAP/Profile UID mismatch"
            )

        elif not self.directory.gid_matches:
            result.append(
                "LDAP/Profile GID mismatch"
            )

        result.extend(
            self.storage.problems
        )

        if not self.kubernetes_ready:
            result.append(
                "Kubernetes identity is "
                "missing or inconsistent"
            )

        return tuple(result)


def inspect_user_directory_identity(
    *,
    profile,
    backend=None,
):
    ldap = backend or Ldap()

    try:
        entry = ldap.get_user(
            profile.user
        )

    except LdapException:
        return UserDirectoryIdentityStatus(
            present=False,
            ldap_uid=None,
            ldap_gid=None,
            uid_matches=False,
            gid_matches=False,
        )

    try:
        uid = int(
            entry.uidNumber.value
        )
        gid = int(
            entry.gidNumber.value
        )

    except (
        AttributeError,
        TypeError,
        ValueError,
    ):
        return UserDirectoryIdentityStatus(
            present=True,
            ldap_uid=None,
            ldap_gid=None,
            uid_matches=False,
            gid_matches=False,
        )

    return UserDirectoryIdentityStatus(
        present=True,
        ldap_uid=uid,
        ldap_gid=gid,
        uid_matches=(
            profile.uid_number == uid
        ),
        gid_matches=(
            profile.gid_number == gid
        ),
    )


def inspect_user_readiness(
    *,
    profile,
    ldap=None,
):
    directory = (
        inspect_user_directory_identity(
            profile=profile,
            backend=ldap,
        )
    )

    storage = inspect_user_storage(
        profile=profile
    )

    kubernetes = tuple(
        inspect_user_kubernetes_identity(
            profile=profile
        )
    )

    if (
        HUB_SETTINGS
        .kubernetes_identity
        .enabled
    ):
        kubernetes_ready = (
            bool(kubernetes)
            and all(
                status.ready
                for status in kubernetes
            )
        )

    else:
        kubernetes_ready = True

    return UserReadinessStatus(
        profile_id=profile.pk,
        username=profile.user.username,
        token_ready=bool(
            profile.token
        ),
        directory=directory,
        storage=storage,
        kubernetes=kubernetes,
        kubernetes_ready=(
            kubernetes_ready
        ),
    )


def reconcile_user(
    *,
    profile,
    fix=False,
):
    if profile.state in {
        Profile.State.DELETING,
        Profile.State.DELETE_FAILED,
    }:
        return inspect_user_readiness(
            profile=profile
        )

    before = inspect_user_readiness(
        profile=profile
    )

    if not fix:
        return before

    DirectoryService().ensure_structure()

    if not profile.token:
        profile.token = pwgen.pwgen(64)

        profile.save(
            update_fields=["token"]
        )

    #
    # Safe now that ensure_user_directory_identity()
    # refuses populated UID/GID conflicts.
    #
    ensure_user_directory_identity(
        profile=profile
    )

    profile.refresh_from_db()

    ensure_user_storage(
        profile=profile
    )

    ensure_user_kubernetes_identity(
        profile=profile
    )

    profile.refresh_from_db()

    after = inspect_user_readiness(
        profile=profile
    )

    if after.ready:
        update = {
            "state": Profile.State.READY,
            "last_operation_error": "",
            "last_operation_failed_at": None,
        }

        if profile.provisioned_at is None:
            update[
                "provisioned_at"
            ] = timezone.now()

        Profile.objects.filter(
            pk=profile.pk
        ).update(**update)

    return after


