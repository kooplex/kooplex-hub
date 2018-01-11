import ldap3

from kooplex.lib import get_settings

class LdapException(Exception):
    pass

class Ldap:
    host = get_settings('ldap', 'host')
    port = get_settings('ldap', 'port')
    base_dn = get_settings('ldap', 'base_dn')
    bind_dn = get_settings('ldap', 'bind_dn')
    bind_pw = get_settings('ldap', 'bind_password')

    def __init__(self):
        server = ldap3.Server(host = self.host, port = self.port)
        self.connection = ldap3.Connection(server, self.bind_dn, self.bind_pw)
        success = self.connection.bind()
        if not success:
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
        return entries

    def modify_user(self, oldentries, newentries):
        assert oldentries[0]['dn'] == newentries[0]['dn']
        dn = newentries[0]['dn']
        changes = {}
        for key, value in newentries[0]['attributes'].items():
            if oldentries[0]['attributes'][key] != value:
                changes[key] = [(ldap3.MODIFY_REPLACE, value)]
        if not self.connection.modify(dn, changes):
            raise LdapException(self.connection.last_error)

    def changepassword(self, user, newpassword, oldpassword = None):
        if oldpassword is not None:
            self.validate_user(user.username, oldpassword)
        oldentries = self.get_user(user)
        newentries = self.get_user(user)
        newentries[0]['attributes']['userPassword'] = [ newpassword ]
        self.modify_user(oldentries, newentries)

    def is_validpassword(self, user, password):
        try:
            entries = self.get_user(user)
            return entries[0]['attributes']['userPassword'][0].decode() == password
        except:
            # user record may be missing
            return False        


####    def get_max_uid(self):
####        print_debug("")
####        filter = '(objectClass=posixAccount)'
####        attributes = ['uidNumber']
####        self.ldapconn.search(
####            search_base=self.base_dn,
####            search_filter=filter,
####            search_scope=ldap3.SUBTREE,
####            attributes=attributes)
####        entries = self.ldapconn.response
#####        uids = ()
#####        for entry in entries:
#####            uids = uids + (int(self.get_attribute(entry, 'uidNumber')), )
#####        return max(uids)
####        return max([ int(self.get_attribute(e, 'uidNumber')) for e in entries ])
####
####    def add_user(self, user):
####        print_debug("")
####        if not hasattr(user, 'uid') or not user.uid:
####            user.uid = self.get_max_gid() + 1
####            user.gid = user.uid
####        dn, object_class, attributes = self.user_to_ldap(user)
####        if not self.ldapconn.add(dn, object_class, attributes):
####            raise LdapException(self.ldapconn.result['description'])
####        group = self.make_user_group(user)
####        self.ensure_group_added(group)
####        return user
####
####    def delete_user(self, user):
####        print_debug("")
####        group = self.make_user_group(user)
####        self.ensure_group_deleted(group)
####        dn = self.get_user_dn(user)
####        if not self.ldapconn.delete(dn):
####            raise LdapException(self.ldapconn.last_error)
####
####    def get_group_name(self, group):
####        print_debug("")
####        if type(group) is str:
####            return group
####        else:
####            return group.name
####
####    def make_user_group(self, user):
####        print_debug("")
####        """Creates posix group associated with the user, using same gid"""
####        g = Group(name = user.username)
####        if hasattr(user, 'gid'):
####            g.gid = user.gid
####        else:
####            g.gid = None
####        if hasattr(user, 'members'):
####            g.members = [ user.username ]
####        else:
####            g.members = []
####        return g
####
####    def get_group_dn(self, group):
####        print_debug("")
####        name = self.get_group_name(group)
####        dn = 'cn=%s,ou=groups,%s' % (name, self.base_dn)
####        return dn
####
####    def group_to_ldap(self, group):
####        print_debug("")
####        dn = self.get_group_dn(group)
####        object_class = [
####            'top',
####            'posixGroup',
####        ]
####        attributes = {
####            'cn': group.name,
####            'gidNumber': group.gid,
####        }
####        if group.members and len(group.members) > 0:
####            attributes['memberUid'] = group.members
####        return dn, object_class, attributes
####
####    def ldap_to_group(self, entry):
####        print_debug("")
####        group = Group(
####            name=self.get_attribute(entry, 'cn')
####        )
####        group.gid = self.get_attribute(entry, 'gidNumber')
####        group.members = self.get_attribute_list(entry, 'memberUid')
####        return group
####
####    def get_max_gid(self):
####        print_debug("")
####        filter = '(|(objectClass=posixAccount)(objectClass=posixGroup))'
####        attributes = ['gidNumber']
####        self.ldapconn.search(
####            search_base=self.base_dn,
####            search_filter=filter,
####            search_scope=ldap3.SUBTREE,
####            attributes=attributes)
####        entries = self.ldapconn.response
####        gids = ()
####        for entry in entries:
####            gids = gids + (int(self.get_attribute(entry, 'gidNumber')), )
####        return max(gids)
####
####    def add_group(self, group):
####        print_debug("")
####        if not hasattr(group, 'gid') or not group.gid:
####            group.gid = self.get_max_gid() + 1
####        dn, object_class, attributes = self.group_to_ldap(group)
####        if not self.ldapconn.add(dn, object_class, attributes):
####            raise LdapException(self.ldapconn.result['description'])
####        return group
####
####    def ensure_group_added(self, group):
####        print_debug("")
####        try:
####            u = self.get_group(group)
####        except LdapException:
####            u = self.add_group(group)
####        return u
####
####    def get_group(self, group):
####        print_debug("")
####        name = self.get_group_name(group)
####        filter = '(&(objectClass=posixGroup)(cn=%s))' % name
####        search_base = 'ou=groups,%s' % self.base_dn
####        self.ldapconn.search(
####            search_base=self.base_dn,
####            search_filter=filter,
####            search_scope=ldap3.SUBTREE,
####            attributes=ldap3.ALL_ATTRIBUTES)
####        entries = self.ldapconn.response
####        if not entries or len(entries) == 0:
####            raise LdapException('no such group')
####        else:
####            group = self.ldap_to_group(entries[0])
####            return group
####
####
####    def delete_group(self, group):
####        print_debug("")
####        dn = self.get_group_dn(group)
####        if not self.ldapconn.delete(dn):
####            raise LdapException(self.ldapconn.last_error)
####
####    def ensure_group_deleted(self, group):
####        print_debug("")
####        try:
####            self.delete_group(group)
####        except LdapException:
####            pass
####
