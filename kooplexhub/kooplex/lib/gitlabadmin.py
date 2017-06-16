import json
import requests
from django.conf import settings
import datetime
from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.libbase import get_settings
from kooplex.lib.debug import *
from django.core.exceptions import ValidationError

from urllib.parse import quote, urlencode

DEBUG_LOCAL=False

class GitlabAdmin(Gitlab):

    ADMIN_USERNAME = get_settings('gitlab', 'admin_username', None, None)
    ADMIN_PASSWORD= get_settings('gitlab', 'admin_password', None, None)
    ADMIN_PRIVATE_TOKEN = None

    def http_prepare_headers(self, headers):
        print_debug("",DEBUG_LOCAL)
        headers = RestClient.http_prepare_headers(self, headers)
        token = self.get_admin_private_token()
        if token:
            headers[Gitlab.HEADER_PRIVATE_TOKEN_KEY] = token
        return headers

    def authenticate_admin(self):
        print_debug("",DEBUG_LOCAL)
        res, user = self.authenticate(GitlabAdmin.ADMIN_USERNAME, GitlabAdmin.ADMIN_PASSWORD)
        if user is not None:
            GitlabAdmin.ADMIN_PRIVATE_TOKEN = user[Gitlab.URL_PRIVATE_TOKEN_KEY]
        return res, user

    def get_admin_private_token(self):
        print_debug("",DEBUG_LOCAL)
        if GitlabAdmin.ADMIN_PRIVATE_TOKEN is None:
            # the following is needed to avoid infinite calls of the method http_prepare_headers
            # by the method self.authenticate:
            GitlabAdmin.ADMIN_PRIVATE_TOKEN = 'in progress'
            self.authenticate_admin()
        return GitlabAdmin.ADMIN_PRIVATE_TOKEN

    ###########################################################
    # User management

    def create_user(self, user):
        print_debug("",DEBUG_LOCAL)
        # TODO: create external user in gitlab via REST API and set
        # identity to point to LDAP
#FIXME: LDAPORG HARDCODED
        url = self.api_version + "/users?name='%(firstname)s %(lastname)s'&username=%(username)s&email=%(email)s&password=%(password)s&confirm=false" % user
#&extern_uid='uid=%(username)s,ou=users,dc=novo1,dc=complex,dc=elte,dc=hu'
        print("URL", url)
        #url += "&confirmed_at=%s" % (strdatetime.time(1))
        res = self.http_post(url)
        print("VVVVVVVVVVVVVVVVVV", res.json())
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def upload_userkey(self, user, key):
        print_debug("",DEBUG_LOCAL)
        print ("HHHHHHHHHHHHHHHH", user)
        print ("HHHHHHHHHHHHHHHH", user['username'])
        resp = self.get_user(user['username'])[0]
        print ("HHHHHHHHHHHHHHHH", resp)
        data = urlencode( { 'key': key.strip() } )
        url = self.api_version + "/users/%d/keys?title=gitlabkey" % (resp['id'])
        res = self.http_post( url, data = data )
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def get_all_users(self):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/users')
        return res.json()

    def check_useradmin(self,username):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/users?username=%s'%username)
#        res = self.http_get('api/v3/users?search=%s'%username)
        user = res.json()
        
        return user[0]['is_admin']

    def modify_user(self, userid, property, value):
        print_debug("",DEBUG_LOCAL)
        url = self.api_version+"/users/%s" % str(userid)
        data = {property:value}
        res = self.http_put(url, params=data)
        if res.status_code > 400:
            raise ValidationError("Password couldn't be changed")
        message = res.json()

        return message

    
    ###########################################################
    # Group management
        
    def get_all_groups(self):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/groups')
        return res.json()
        
    def get_group_members(self,id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/groups/%s/members'%str(id))
        return res.json()


    ###########################################################
    # Projects

    def get_all_projects(self):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/projects?page=1&per_page=1000')
        projects_json = res.json()
        if 'message' in projects_json:
            raise ValueError("MESSAGE: %s"%(projects_json['message']))
        return projects_json

#    def get_project(self, project_id):
#        print_debug("",DEBUG_LOCAL)
#        res = self.http_get('api/v3/projects/%s'%project_id)
#        project_json = res.json()
#        if 'message' in project_json:
#            raise ValueError("MESSAGE: %s"%(projects_json['message']))
#        return project_json

    #THERE IS A PROBLEM IN NAMING WITH THE TWO FOLLOWING
    def get_public_projects(self, unforkable_projectids):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/projects')
        public_projects_json = res.json()
        if 'message' in public_projects_json:
            raise ValueError("MESSAGE: %s"%(public_projects_json['message']))
        self.identify_unforkable_projects(public_projects_json, unforkable_projectids)
        return public_projects_json

    def get_all_public_projects(self, unforkable_projectids):
        print_debug("",DEBUG_LOCAL)
        #res = self.http_get(self.api_version+'/projects/all?visibility=public')
        res = self.http_get(self.api_version+'/projects/')
        public_projects_json = res.json()
        if 'message' in public_projects_json:
            raise ValueError("MESSAGE: %s"%(public_projects_json['message']))
        self.identify_unforkable_projects(public_projects_json, unforkable_projectids)
        return public_projects_json

    def identify_unforkable_projects(self, public_projects_json, unforkable_projectids):
        print_debug("",DEBUG_LOCAL)
        for project in public_projects_json:
            if project['id'] in unforkable_projectids:
                project['forkable'] = False
            else:
                project['forkable'] = True
        return public_projects_json
        
    def get_project_variables(self,project_id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/projects/%d/variables'%(project_id))
        project_variables = res.json()
        return project_variables
