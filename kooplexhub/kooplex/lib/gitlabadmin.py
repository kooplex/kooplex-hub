import json
import requests
from django.conf import settings

from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.libbase import get_settings
from kooplex.lib.debug import *
from django.core.exceptions import ValidationError

class GitlabAdmin(Gitlab):

    ADMIN_USERNAME = get_settings('gitlab', 'admin_username', None, None)
    ADMIN_PASSWORD= get_settings('gitlab', 'admin_password', None, None)
    ADMIN_PRIVATE_TOKEN = None

    def http_prepare_headers(self, headers):
        print_debug("")
        headers = RestClient.http_prepare_headers(self, headers)
        token = self.get_admin_private_token()
        if token:
            headers[Gitlab.HEADER_PRIVATE_TOKEN_KEY] = token
        return headers

    def authenticate_admin(self):
        print_debug("")
        res, user = self.authenticate(GitlabAdmin.ADMIN_USERNAME, GitlabAdmin.ADMIN_PASSWORD)
        if user is not None:
            GitlabAdmin.ADMIN_PRIVATE_TOKEN = user[Gitlab.URL_PRIVATE_TOKEN_KEY]
        return res, user

    def get_admin_private_token(self):
        print_debug("")
        if GitlabAdmin.ADMIN_PRIVATE_TOKEN is None:
            # the following is needed to avoid infinite calls of the method http_prepare_headers
            # by the method self.authenticate:
            GitlabAdmin.ADMIN_PRIVATE_TOKEN = 'in progress'
            self.authenticate_admin()
        return GitlabAdmin.ADMIN_PRIVATE_TOKEN

    ###########################################################
    # User management

    def create_user(self, user):
        print_debug("")
        # TODO: create external user in gitlab via REST API and set
        # identity to point to LDAP
        return None

    def get_all_users(self):
        print_debug("")
        res = self.http_get('api/v3/users')
        return res.json()

    def check_useradmin(self,username):
        print_debug("")
        res = self.http_get('api/v3/users?username=%s'%username)
#        res = self.http_get('api/v3/users?search=%s'%username)
        user = res.json()
        return user[0]['is_admin']

    def modify_user(self, userid, property, value):
        print_debug("")
        url = "api/v3/users/%s" % str(userid)
        data = {property:value}
        res = self.http_put(url, params=data)
        if res.status_code > 400:
            raise ValidationError("Password couldn't be changed")
        message = res.json()

        return message

    
    ###########################################################
    # Group management
        
    def get_all_groups(self):
        print_debug("")
        res = self.http_get('api/v3/groups')
        return res.json()
        
    def get_group_members(self,id):
        print_debug("")
        res = self.http_get('api/v3/groups/%s/members'%str(id))
        return res.json()


    ###########################################################
    # Projects

    def get_all_projects(self):
        print_debug("")
        res = self.http_get('api/v3/projects/all')
        projects_json = res.json()
        if 'message' in projects_json:
            raise ValueError("MESSAGE: %s"%(projects_json['message']))
        return projects_json
        
    def get_all_public_projects(self, unforkable_projectids):
        print_debug("")
        res = self.http_get('api/v3/projects/all?visibility=public')
        public_projects_json = res.json()
        if 'message' in public_projects_json:
            raise ValueError("MESSAGE: %s"%(public_projects_json['message']))
        self.identify_unforkable_projects(public_projects_json, unforkable_projectids)
        return public_projects_json

    def identify_unforkable_projects(self, public_projects_json, unforkable_projectids):
        print_debug("")
        for project in public_projects_json:
            if project['id'] in unforkable_projectids:
                project['forkable'] = False
            else:
                project['forkable'] = True
        return public_projects_json
        
    def get_project_members(self,id):
        print_debug("")
        res = self.http_get('api/v3/projects/%s/members'%str(id))
        return res.json()