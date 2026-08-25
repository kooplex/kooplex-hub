from dataclasses import dataclass

from ldap3.utils.dn import parse_dn

from hub.conf import HUB_SETTINGS
from hub.lib.ldap import Ldap


class DirectoryProvisioningError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class DirectoryStructureStatus:
    base_exists: bool
    users_exists: bool
    groups_exists: bool

    @property
    def ready(self):
        return (
            self.base_exists
            and self.users_exists
            and self.groups_exists
        )


class DirectoryService:

    def __init__(self, backend=None):
        self.backend = backend or Ldap()

    def check_structure(self):
        ldap = HUB_SETTINGS.ldap

        return DirectoryStructureStatus(
            base_exists=self.backend.exists(
                ldap.base_dn
            ),
            users_exists=self.backend.exists(
                ldap.user_search
            ),
            groups_exists=self.backend.exists(
                ldap.group_search
            ),
        )

    def ensure_structure(self):
        status = self.check_structure()

        if not status.base_exists:
            raise DirectoryProvisioningError(
                f"LDAP base DN does not exist: "
                f"{HUB_SETTINGS.ldap.base_dn}. "
                "The LDAP server itself must be initialized first."
            )

        created = []

        if not status.users_exists:
            self._create_ou(
                HUB_SETTINGS.ldap.user_search
            )
            created.append(
                HUB_SETTINGS.ldap.user_search
            )

        if not status.groups_exists:
            self._create_ou(
                HUB_SETTINGS.ldap.group_search
            )
            created.append(
                HUB_SETTINGS.ldap.group_search
            )

        return tuple(created)

    def _create_ou(self, dn):
        parsed = parse_dn(
            dn,
            escape=True,
            strip=True,
        )

        if not parsed:
            raise DirectoryProvisioningError(
                f"Invalid LDAP DN: {dn}"
            )

        attribute, value, _separator = parsed[0]

        if attribute.lower() != "ou":
            raise DirectoryProvisioningError(
                f"Expected an OU DN, got: {dn}"
            )

        self.backend.add_organizational_unit(
            dn=dn,
            name=value,
        )


