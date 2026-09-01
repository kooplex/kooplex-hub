import ldap3
import logging
from ldap3.utils.conv import escape_filter_chars
from ldap3.utils.dn import escape_rdn

from ..conf import HUB_SETTINGS

logger = logging.getLogger(__name__)


class LdapException(Exception):
    pass

class Ldap:

    def __init__(self):
        conf = HUB_SETTINGS.ldap

        self.host = conf.host
        self.port = conf.port

        self.base_dn = conf.base_dn
        self.bind_dn = conf.bind_dn
        self.bind_pw = conf.bind_password

        self.user_dn_template = conf.user_dn
        self.group_dn_template = conf.group_dn

        self.user_search = conf.user_search
        self.group_search = conf.group_search

        server = ldap3.Server(
            host=self.host, 
            port=self.port,
        )

        self.connection = ldap3.Connection(
            server, 
            self.bind_dn, 
            self.bind_pw,
        )

        if not self.connection.bind():
            self._raise(
                "Cannot bind to ldap server: "
                f"{self.host}:{self.port}"
            )

    def _raise(self, message):
        result = self.connection.result or {}

        description = result.get(
            "description",
            "unknown LDAP error",
        )

        ldap_message = result.get("message", "")
        code = result.get("result")

        detail = f"{description}"

        if code is not None:
            detail += f" ({code})"

        if ldap_message:
            detail += f": {ldap_message}"

        raise LdapException(
            f"{message}: {detail}"
        )

    def user_dn(self, user):
        return self.user_dn_template.format(
            username=escape_rdn(user.username),
        )

    def group_dn(self, group):
        return self.group_dn_template.format(
            groupname=escape_rdn(group.name),
        )

    def exists(self, dn):
        self.connection.search(
            search_base=dn,
            search_filter="(objectClass=*)",
            search_scope=ldap3.BASE,
            attributes=["objectClass"],
        )

        result = self.connection.result or {}

        if result.get("result") == 32:
            return False

        if result.get("result") != 0:
            self._raise(
                f"Could not inspect LDAP entry {dn}"
            )

        return bool(self.connection.entries)


    def add_organizational_unit(self, *, dn, name):
        if self.exists(dn):
            return False
    
        success = self.connection.add(
            dn,
            object_class=[
                "top",
                "organizationalUnit",
            ],
            attributes={
                "ou": name,
            },
        )

        if not success:
            self._raise(
                f"Could not create LDAP organizational unit {dn}"
            )

        return True


    def get_user(self, user):
        username = escape_filter_chars(
            user.username
        )

        filter_expression = (
            "(&(objectClass=posixAccount)"
            f"(uid={username}))"
        )

        self.connection.search(
            search_base=self.user_search,
            search_filter=filter_expression,
            search_scope=ldap3.SUBTREE,
            attributes=ldap3.ALL_ATTRIBUTES,
        )

        entries = self.connection.entries

        if not entries:
            raise LdapException(
                f"No such LDAP user: {user.username}"
            )

        if len(entries) != 1:
            raise LdapException(
                f"Expected one LDAP user for "
                f"{user.username}, got {len(entries)}."
            )

        return entries[0]


    def add_user(
        self, 
        *,
        user,
        uid_number,
        gid_number,
    ):
        dn = HUB_SETTINGS.ldap.user_dn.format(
            username=user.username
        )

        logger.info(
            "Creating LDAP user %s",
            dn,
        )

        object_classes = [
            "top",
            "posixAccount",
            "inetOrgPerson",
        ]

        attributes = {
            "cn": user.username,
            "uid": user.username,
            "sn": user.username,
            "uidNumber": uid_number,
            "gidNumber": gid_number,
            "homeDirectory": (
                HUB_SETTINGS
                .mounts
                .home
                .mountpoint
                .format(user=user)
            ),
            "loginShell": "/bin/bash",
        }

        if not self.connection.add(
            dn,
            object_classes,
            attributes,
        ):
            self._raise(
                f"Could not create LDAP user {user.username}"
            )


    def delete_dn(self, dn):
        if not self.connection.delete(dn):
            self._raise(
                f"Could not delete LDAP entry {dn}"
            )


    def remove_user(self, user):
        self.remove_user_by_username(user.username)


    def remove_user_by_username(self, username):
        dn = self.user_dn_template.format(
            username=escape_rdn(username),
        )
        self.delete_dn(dn)
        logger.info(
            "Deleted LDAP user %s",
            dn,
        )


    def get_group(self, group):
        groupname = escape_filter_chars(
            group.name
        )

        filter_expression = (
            "(&(objectClass=posixGroup)"
            f"(cn={groupname}))"
        )

        self.connection.search(
            search_base=self.group_search,
            search_filter=filter_expression,
            search_scope=ldap3.SUBTREE,
            attributes=ldap3.ALL_ATTRIBUTES,
        )

        entries = self.connection.entries

        if not entries:
            raise LdapException(
                f"No such LDAP group: {group.name}"
            )

        if len(entries) != 1:
            raise LdapException(
                f"Expected one LDAP group for "
                f"{group.name}, got {len(entries)}."
            )

        return entries[0]


    def add_group(self, group):
        dn = self.group_dn(group)

        logger.info(
            "Creating LDAP group %s gid=%s",
            dn,
            group.groupid,
        )

        object_classes = [
            "top",
            "posixGroup",
        ]

        attributes = {
            "cn": group.name,
            "gidNumber": group.groupid,
        }

        if not self.connection.add(
            dn,
            object_classes,
            attributes,
        ):
            self._raise(
                f"Could not create LDAP group {group.name}"
            )


    def remove_group(self, group):
        self.remove_group_by_name(group.name)
        logger.info(
            "Deleted LDAP group %s gid=%s",
            dn,
            group.groupid,
        )


    def remove_group_by_name(self, groupname):
        dn = self.group_dn_template.format(
            groupname=escape_rdn(groupname),
        )
        self.connection.delete(dn)
        logger.info(
            "Deleted LDAP group %s",
            dn,
        )


    def add_user_to_group(
        self,
        user,
        group,
    ):
        dn = self.group_dn(group)

        changes = {
            "memberUid": (
                ldap3.MODIFY_ADD,
                [user.username],
            )
        }

        if not self.connection.modify(
            dn,
            changes,
        ):
            self._raise(
                f"Could not add {user.username} "
                f"to LDAP group {group.name}"
            )


    def remove_user_from_group(
        self,
        user,
        group,
    ):
        dn = self.group_dn(group)

        changes = {
            "memberUid": (
                ldap3.MODIFY_DELETE,
                [user.username],
            )
        }

        if not self.connection.modify(
            dn,
            changes,
        ):
            self._raise(
                f"Could not remove {user.username} "
                f"from LDAP group {group.name}"
            )


    def has_user(self, username):
        username = escape_filter_chars(username)
    
        self.connection.search(
            search_base=self.user_search,
            search_filter=(
                "(&(objectClass=posixAccount)"
                f"(uid={username}))"
            ),
            search_scope=ldap3.SUBTREE,
            attributes=["uid"],
        )
    
        return len(self.connection.entries) == 1


    def users(self):
        self.connection.search(
            search_base=self.user_search,
            search_filter="(objectClass=posixAccount)",
            search_scope=ldap3.SUBTREE,
            attributes=[
                "uid",
                "uidNumber",
                "gidNumber",
            ],
        )

        return tuple(self.connection.entries)


    def groups(self):
        self.connection.search(
            search_base=self.group_search,
            search_filter="(objectClass=posixGroup)",
            search_scope=ldap3.SUBTREE,
            attributes=[
                "cn",
                "gidNumber",
                "memberUid",
            ],
        )

        return tuple(self.connection.entries)

