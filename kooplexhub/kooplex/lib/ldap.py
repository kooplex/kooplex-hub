import ldap3
import logging

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

class LdapException(Exception):
    pass

class Ldap:

    def __init__(self):
        logger.debug("init")
        ldapconf = KOOPLEX.get('ldap', {})
        self.host = ldapconf.get('host', 'localhost')
        self.port = ldapconf.get('port', 389)
        try:
            self.base_dn = ldapconf['base_dn']
            self.bind_dn = ldapconf['bind_dn']
            self.bind_pw = ldapconf['bind_password']
        except KeyError as e:
            logger.error("Cannot initialize ldap, KOOPLEX['ldap'][key] key is missing -- %s" % e)
            raise
        server = ldap3.Server(host = self.host, port = self.port)
        self.connection = ldap3.Connection(server, self.bind_dn, self.bind_pw)
        success = self.connection.bind()
        if not success:
            logger.error("Cannot bind to ldap server")
            raise LdapException("Cannot bind to ldap server")

    def get_user(self, user):
        filter_expression = '(&(objectClass=posixAccount)(uid=%s))' % user.username
        search_base = 'ou=users,%s' % self.base_dn
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

    def userdn(self, user):
        return 'uid=%s,ou=users,%s' % (user.username, self.base_dn)

    def adduser(self, user):
        logging.debug('add %s' % user)
        dn = self.userdn(user)
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
            'homeDirectory': '/home/%s' % user.username,
            'loginShell': '/bin/bash',
        }
        success = self.connection.add(dn, object_class, attributes)
        if not success:
            raise LdapException(self.connection.result['description'])

    def removeuser(self, user):
        logging.debug('remove %s' % user)
        dn = self.userdn(user)
        if not self.connection.delete(dn):
            raise LdapException(self.connection.result['description'])

    def get_group(self, group):
        filter_expression = '(&(objectClass=posixGroup)(cn=%s))' % group.name
        search_base = 'ou=groups,%s' % self.base_dn
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

    def groupdn(self, group):
        return 'cn=%s,ou=groups,%s' % (group.name, self.base_dn)

    def addgroup(self, group):
        logging.debug('add %s' % group)
        dn = self.groupdn(group)
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
        logging.debug('remove %s' % group)
        dn = self.groupdn(group)
        if not self.connection.delete(dn):
            raise LdapException(self.connection.result['description'])

    def addusertogroup(self, user, group):
        dn = self.groupdn(group)
        changes = { 'memberUid': (ldap3.MODIFY_ADD, user.username) }
        if not self.connection.modify(dn, changes):
            raise LdapException(self.connection.result['description'])

    def removeuserfromgroup(self, user, group):
        dn = self.groupdn(group)
        changes = { 'memberUid': (ldap3.MODIFY_DELETE, user.username) }
        if not self.connection.modify(dn, changes):
            raise LdapException(self.connection.result['description'])
