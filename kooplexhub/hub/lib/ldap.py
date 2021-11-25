import ldap3
import logging

from kooplexhub.settings import KOOPLEX

logger = logging.getLogger(__name__)


class LdapException(Exception):
    pass

class Ldap:

    def __init__(self):
        logger.debug("init")
        ldapconf = KOOPLEX.get('ldap', {})
        self.host = ldapconf.get('host', 'localhost')
        self.port = ldapconf.get('port', 389)
        self.userdn = ldapconf.get('userdn', 'uid={user.username},ou=users,dn=localhost')
        self.groupdn = ldapconf.get('groupdn', 'uid={group.name},ou=users,dn=localhost')
        self.base_dn = ldapconf.get('base_dn', 'dn=localhost')
        self.bind_dn = ldapconf.get('bind_dn', 'cn=admin,dn=localhost')
        self.bind_pw = ldapconf.get('bind_password')
        server = ldap3.Server(host = self.host, port = self.port)
        self.connection = ldap3.Connection(server, self.bind_dn, self.bind_pw)
        success = self.connection.bind()
        if not success:
            logger.error("Cannot bind to ldap server")
            raise LdapException("Cannot bind to ldap server")

    def get_user(self, user):
        filter_expression = '(&(objectClass=posixAccount)(uid={}))'.format(user.username)
        search_base = KOOPLEX.get('ldap', {}).get('usersearch', 'ou=users,dn=localhost')
        self.connection.search(
            search_base = self.base_dn,
            search_filter = filter_expression,
            search_scope = ldap3.SUBTREE,
            attributes = ldap3.ALL_ATTRIBUTES)
        entries = self.connection.response
        if not entries or len(entries) == 0:
            raise LdapException('no such user')
        assert len(entries) == 1, "More than 1 entry!"
        return entries[0]


    def adduser(self, user):
        logging.debug('add {}'.format(user))
        dn = self.userdn.format(user = user)
        object_class = [
            'top',
            'posixAccount',
            'inetOrgPerson',
        ]
        attributes = {
            'cn': user.username,
            'uid': user.username,
            'sn': user.username,
            'uidNumber': user.profile.userid,
            'gidNumber': user.profile.groupid,
            'homeDirectory': KOOPLEX.get('userdata', {}).get('mountPath_home', '/home/{user.username}').format(user = user),
            'loginShell': '/bin/bash',
        }
        success = self.connection.add(dn, object_class, attributes)
        if not success:
            raise LdapException(self.connection.result['description'])

    def removeuser(self, user):
        logging.debug('remove {}'.format(user))
        dn = self.userdn.format(user = user)
        if not self.connection.delete(dn):
            raise LdapException(self.connection.result['description'])

    def get_group(self, group):
        filter_expression = '(&(objectClass=posixGroup)(cn={}))'.format(group.name)
        search_base = KOOPLEX.get('ldap', {}).get('groupsearch', 'ou=groups,dn=localhost')
        self.connection.search(
            search_base = self.base_dn,
            search_filter = filter_expression,
            search_scope = ldap3.SUBTREE,
            attributes = ldap3.ALL_ATTRIBUTES)
        entries = self.connection.response
        if not entries or len(entries) == 0:
            raise LdapException('no such group')
        assert len(entries) == 1, "More than 1 entry!"
        return entries[0]


    def addgroup(self, group):
        dn = self.groupdn.format(group = group)
        logging.debug('add {} -> {}'.format(group, dn))
        object_class = [
            'top',
            'posixGroup',
        ]
        attributes = {
            'cn': group.name,
            'gidNumber': group.groupid,
        }
        success = self.connection.add(dn, object_class, attributes)
        if not success:
            raise LdapException(self.connection.result['description'])

    def removegroup(self, group):
        logging.debug('remove {}'.format(group))
        dn = self.groupdn.format(group = group)
        if not self.connection.delete(dn):
            raise LdapException(self.connection.result['description'])

    def addusertogroup(self, user, group):
        dn = self.groupdn.format(group = group)
        changes = { 'memberUid': (ldap3.MODIFY_ADD, user.username) }
        if not self.connection.modify(dn, changes):
            raise LdapException(self.connection.result['description'])

    def removeuserfromgroup(self, user, group):
        dn = self.groupdn.format(group = group)
        changes = { 'memberUid': (ldap3.MODIFY_DELETE, user.username) }
        if not self.connection.modify(dn, changes):
            raise LdapException(self.connection.result['description'])
