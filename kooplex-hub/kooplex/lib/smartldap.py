import ldap3
from kooplex.lib import LibBase, get_settings
from django.contrib.auth.models import User, Group

class LdapException(Exception):
    pass

class Ldap(LibBase):
    
    def __init__(self):
        self.host = get_settings('KOOPLEX_LDAP', 'host')
        self.port = get_settings('KOOPLEX_LDAP', 'port', None, 389)
        self.base_dn = get_settings('KOOPLEX_LDAP', 'base_dn')
        self.bind_username = get_settings('KOOPLEX_LDAP', 'bind_username')
        self.bind_password = get_settings('KOOPLEX_LDAP', 'bind_password')
        self.user_home_dir = get_settings('KOOPLEX_USERS', 'home_dir')

        self.ldapconn = self.make_ldap_client()

    def make_ldap_client(self):
        bind_dn = 'cn=%s,%s' % (self.bind_username, self.base_dn)
        ldapsrv = ldap3.Server(host=self.host, port=self.port)
        ldapcon = ldap3.Connection(ldapsrv, bind_dn, self.bind_password)
        success = ldapcon.bind()
        if not success:
            raise Exception
        return ldapcon

    def get_attribute(self, entry, attribute):
        attrs = entry['attributes']
        if attribute in attrs:
            return attrs[attribute][0]
        else:
            return None

    def get_attribute_list(self, entry, attribute):
        attrs = entry['attributes']
        if attribute in attrs:
            return attrs[attribute]
        else:
            return []

    ###########################################################
    # User manipulation

    def get_user_name(self, user):
        if type(user) is str:
            return user
        else:
            return user.username

    def get_user_dn(self, user):
        username = self.get_user_name(user)
        dn = 'uid=%s,ou=users,%s' % (username, self.base_dn)
        return dn

    def user_to_ldap(self, user):
        dn = self.get_user_dn(user)
        object_class = [
            'top',
            'simpleSecurityObject',
            'organizationalPerson',
            'person',
            'inetOrgPerson',
            'posixAccount',
            'shadowAccount',
        ]
        attributes = {
            'cn': user.username,
            'uid': user.username,
            'uidNumber': user.uid,
            'gidNumber': user.gid,
            'homeDirectory': self.user_home_dir.replace('{$username}', user.username),
            'sn': user.last_name,
            'displayName': '%s %s' % (user.first_name, user.last_name),
            'givenName': user.first_name,
            'loginShell': '/bin/bash',
            'mail': user.email,
            'shadowExpire': -1,
            'shadowFlag': 0,
            'shadowLastChange': 10877,
            'shadowMax': 999999,
            'shadowMin': 8,
            'shadowWarning': 7,
            'userPassword': user.password
        }
        return dn, object_class, attributes

    def ldap_to_user(self, entry):
        user = User(
            username=self.get_attribute(entry, 'uid'),
            first_name=self.get_attribute(entry, 'givenName'),
            last_name=self.get_attribute(entry, 'sn'),
            email=self.get_attribute(entry, 'mail')
        )
        user.uid = self.get_attribute(entry, 'uidNumber')
        user.gid = self.get_attribute(entry, 'gidNumber')
        return user

    def get_max_uid(self):
        filter = '(objectClass=posixAccount)'
        attributes = ['uidNumber']
        self.ldapconn.search(
            search_base=self.base_dn,
            search_filter=filter,
            search_scope=ldap3.SUBTREE,
            attributes=attributes)
        entries = self.ldapconn.response
        uids = ()
        for entry in entries:
            uids = uids + (int(self.get_attribute(entry, 'uidNumber')), )
        return max(uids)

    def add_user(self, user):
        if not hasattr(user, 'uid') or not user.uid:
            user.uid = self.get_max_gid() + 1
            user.gid = user.uid
        dn, object_class, attributes = self.user_to_ldap(user)
        if not self.ldapconn.add(dn, object_class, attributes):
            raise LdapException(self.ldapconn.result['description'])
        return user

    def ensure_user_added(self, user):
        try:
            u = self.get_user(user)
        except LdapException:
            u = self.add_user(user)
        return u

    def get_user(self, user):
        username = self.get_user_name(user)
        filter = '(&(objectClass=posixAccount)(uid=%s))' % username
        search_base = 'ou=users,%s' % self.base_dn
        self.ldapconn.search(
            search_base=self.base_dn,
            search_filter=filter,
            search_scope=ldap3.SUBTREE,
            attributes=ldap3.ALL_ATTRIBUTES)
        entries = self.ldapconn.response
        if not entries or len(entries) == 0:
            raise LdapException('no such user')
        else:
            user = self.ldap_to_user(entries[0])
            return user

    def modify_user(self, user):
        dn, _, attributes = self.user_to_ldap(user)
        changes = {}
        for key in attributes:
            changes[key] = [(ldap3.MODIFY_REPLACE, [attributes[key]])]
        if not self.ldapconn.modify(dn, changes):
            raise LdapException(self.ldapconn.last_error)
        return user

    def delete_user(self, user):
        dn = self.get_user_dn(user)
        if not self.ldapconn.delete(dn):
            raise LdapException(self.ldapconn.last_error)

    def ensure_user_deleted(self, user):
        try:
            self.delete_user(user)
        except LdapException:
            pass

    ###########################################################
    # Group manipulation

    def get_group_name(self, group):
        if type(group) is str:
            return group
        else:
            return group.name

    def get_group_dn(self, group):
        name = self.get_group_name(group)
        dn = 'cn=%s,ou=groups,%s' % (name, self.base_dn)
        return dn

    def group_to_ldap(self, group):
        dn = self.get_group_dn(group)
        object_class = [
            'top',
            'posixGroup',
        ]
        attributes = {
            'cn': group.name,
            'gidNumber': group.gid,
        }
        if group.members and len(group.members) > 0:
            attributes['memberUid'] = group.members
        return dn, object_class, attributes

    def ldap_to_group(self, entry):
        group = Group(
            name=self.get_attribute(entry, 'cn')
        )
        group.gid = self.get_attribute(entry, 'gidNumber')
        group.members = self.get_attribute_list(entry, 'memberUid')
        return group

    def get_max_gid(self):
        filter = '(|(objectClass=posixAccount)(objectClass=posixGroup))'
        attributes = ['gidNumber']
        self.ldapconn.search(
            search_base=self.base_dn,
            search_filter=filter,
            search_scope=ldap3.SUBTREE,
            attributes=attributes)
        entries = self.ldapconn.response
        gids = ()
        for entry in entries:
            gids = gids + (int(self.get_attribute(entry, 'gidNumber')), )
        return max(gids)

    def add_group(self, group):
        if not hasattr(group, 'gid') or not group.gid:
            group.gid = self.get_max_gid() + 1
        dn, object_class, attributes = self.group_to_ldap(group)
        if not self.ldapconn.add(dn, object_class, attributes):
            raise LdapException(self.ldapconn.result['description'])
        return group

    def ensure_group_added(self, group):
        try:
            u = self.get_group(group)
        except LdapException:
            u = self.add_group(group)
        return u

    def get_group(self, group):
        name = self.get_group_name(group)
        filter = '(&(objectClass=posixGroup)(cn=%s))' % name
        search_base = 'ou=groups,%s' % self.base_dn
        self.ldapconn.search(
            search_base=self.base_dn,
            search_filter=filter,
            search_scope=ldap3.SUBTREE,
            attributes=ldap3.ALL_ATTRIBUTES)
        entries = self.ldapconn.response
        if not entries or len(entries) == 0:
            raise LdapException('no such group')
        else:
            group = self.ldap_to_group(entries[0])
            return group

    def modify_group(self):
        pass

    def delete_group(self, group):
        dn = self.get_group_dn(group)
        if not self.ldapconn.delete(dn):
            raise LdapException(self.ldapconn.last_error)

    def ensure_group_deleted(self, group):
        try:
            self.delete_group(group)
        except LdapException:
            pass

    ###########################################################
    # Group membership

    def add_user_group(self):
        pass

    def remove_user_group(self):
        pass