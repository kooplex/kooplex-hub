from __future__ import annotations

from dataclasses import dataclass, field

from django.conf import settings

from hub.confutils import merge_dataclass
from hub.conf_types import (
    MountSettings,
    ArchivableMountSettings,
)


@dataclass(frozen=True)
class LdapSettings:
    host: str = "localhost"
    port: int = 389

    base_dn: str = "dn=localhost"
    bind_dn: str = "cn=admin,dn=localhost"
    bind_password: str | bool = False

    user_dn: str = (
        "uid={username},ou=users,dn=localhost"
    )
    group_dn: str = (
        "cn={groupname},ou=groups,dn=localhost"
    )

    user_search: str = "ou=users,dn=localhost"
    group_search: str = "ou=groups,dn=localhost"

    manage_users: bool = False
    manage_group: bool = False

    user_uid_offset: int = 100_000
    user_gid_number: int = 1000

    offsets: dict[str, int] = field(
        default_factory=lambda: {
            "project": 10000,
            "course": 20000,
            "volume": 30000,
        }
    )


@dataclass(
    frozen=True,
    slots=True,
)
class LiveSettings:
    path: str = "hub/ws/live/"
    refresh_debounce_ms: int = 300
    reconnect_initial_ms: int = 500
    reconnect_max_ms: int = 10_000

    @property
    def public_path(self) -> str:
        return f"/{self.path.lstrip('/')}"


def _default_home_mount():
    return ArchivableMountSettings(
        claim="userdata",
        subpath="home",
        folder="{user.username}",
        mountpoint="/home/{user.username}",
        mountpoint_hub="/mnt/home",
        archive_name="user-{user.username}.{time}.tar.gz",
    )


def _default_garbage_mount():
    return MountSettings(
        claim="userdata",
        subpath="garbage",
        folder="{user.username}",
        mountpoint="/garbage/{user.username}",
        mountpoint_hub="/mnt/garbage",
    )


def _default_scratch_mount():
    return MountSettings(
        claim="userdata",
        subpath="scratch",
        folder="{user.username}",
        mountpoint="/scratch/{user.username}",
        mountpoint_hub="/mnt/scratch",
    )


@dataclass(frozen=True)
class MountsSettings:
    home: ArchivableMountSettings = field(
        default_factory=_default_home_mount
    )
    garbage: MountSettings | None = field(
        default_factory=_default_garbage_mount
    )
    scratch: MountSettings | None = field(
        default_factory=_default_scratch_mount
    )


@dataclass(frozen=True)
class MailSettings:
    smtp_server: str = 'localhost'
    email_sender: str = 'admin@localhost'


@dataclass(frozen=True)
class KubernetesIdentitySettings:
    enabled: bool = True

    secret_namespaces: tuple[str, ...] = ()

    job_token_key: str = "job_token"


@dataclass(frozen=True, slots=True)
class HubSettings:
    live: LiveSettings = field(
        default_factory=LiveSettings
    )

    ldap: LdapSettings = field(
        default_factory=LdapSettings
    )

    mail: MailSettings = field(
        default_factory=MailSettings
    )

    archive_home: bool = False

    mounts: MountsSettings = field(
        default_factory=MountsSettings
    )

    kubernetes_identity: KubernetesIdentitySettings = field(
        default_factory=KubernetesIdentitySettings
    )



HUB_SETTINGS = merge_dataclass(
    HubSettings(),
    getattr(settings, "KOOPLEX", {}).get("hub", {}),
)

