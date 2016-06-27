import unittest
from kooplex.lib.smartldap import Ldap, LdapException
from django.contrib.auth.models import User, Group

class Test_ldap(unittest.TestCase):
    
    def make_testuser(self):
        u = User(
            username='testuser',
            first_name='test',
            last_name='testing',
            email='test@kooplex.org'
        )
        u.password='almafa137'
        return u

    def make_testgroup(self):
        g = Group(
            name='testgroup',
        )
        g.members = []
        return g

    def test_make_ldap_client(self):
        l = Ldap()

    def test_get_max_gid(self):
        l = Ldap()
        m = l.get_max_gid()
        self.assertTrue(m > 10000)

    def test_get_max_uid(self):
        l = Ldap()
        m = l.get_max_uid()
        self.assertTrue(m > 10000)

    def test_add_get_delete_user(self):
        l = Ldap()
        u = self.make_testuser()

        l.ensure_user_deleted(u)

        l.add_user(u)
        u = l.get_user(u)
        l.delete_user(u)
        with self.assertRaises(LdapException):
            l.get_user(u)

        l.ensure_user_deleted(u)

    def test_add_existing_user(self):
        l = Ldap()
        u = self.make_testuser()

        l.ensure_user_deleted(u)

        l.add_user(u)
        with self.assertRaises(LdapException):
            l.add_user(u)

        l.ensure_user_deleted(u)

    def test_ensure_user_added(self):
        l = Ldap()
        u = self.make_testuser()

        l.ensure_user_deleted(u)

        l.ensure_user_added(u)
        l.ensure_user_added(u)

        l.ensure_user_deleted(u)

    def test_modify_user(self):
        l = Ldap()
        u = self.make_testuser()

        u = l.ensure_user_added(u)

        u.email = 'updated@kooplex.org'
        u = l.modify_user(u)
        u = l.get_user(u)
        self.assertEqual('updated@kooplex.org', u.email)

        l.ensure_user_deleted(u)

    def test_add_get_delete_group(self):
        l = Ldap()
        g = self.make_testgroup()

        l.ensure_group_deleted(g)

        l.add_group(g)
        g = l.get_group(g)
        l.delete_group(g)
        with self.assertRaises(LdapException):
            l.get_group(g)

        l.ensure_group_deleted(g)
    
    def test_add_existing_group(self):
        l = Ldap()
        g = self.make_testgroup()

        l.ensure_group_deleted(g)
        l.add_group(g)
        with self.assertRaises(LdapException):
            l.add_group(g)

        l.ensure_group_deleted(g)

    def test_ensure_group_added(self):
        l = Ldap()
        g = self.make_testgroup()

        l.ensure_group_deleted(g)

        l.ensure_group_added(g)
        l.ensure_group_added(g)

        l.ensure_group_deleted(g)

if __name__ == '__main__':
    unittest.main()
