import json
import requests
from django.conf import settings
import datetime
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.libbase import get_settings
from django.core.exceptions import ValidationError

from urllib.parse import quote, urlencode

DEBUG_LOCAL=False
#FIXME:
def print_debug(*v, **w): pass
RestClient = object
LibBase = object

class GitlabAdmin(Gitlab):

    ADMIN_USERNAME = get_settings('gitlab', 'admin_username')
    ADMIN_PASSWORD= get_settings('gitlab', 'admin_password')
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
        url = self.api_version + "/users?name='%(first_name)s %(last_name)s'&username=%(username)s&email=%(email)s&password=%(password)s&confirm=false" % (user)
        res = self.http_post(url)
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def upload_userkey(self, user, key):
        print_debug("",DEBUG_LOCAL)
        resp = self.get_user(user)[0]
        data = urlencode( { 'key': key.strip() } )
        url = self.api_version + "/users/%d/keys?title=gitlabkey" % (resp['id'])
        res = self.http_post( url, data = data )
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def delete_user(self, username):
        print_debug("",DEBUG_LOCAL)
        respdict = self.get_user(username)[0]
        url = self.api_version + "/users/%d?hard_delete=true" % respdict['id']
        res = self.http_delete(url)
        return "" if res.status_code in [ 204, 201 ] else res.json()

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


def create_project(project, request):
    g = Gitlab(request)
    g.create_project(project.name, project.scope.name, project.description)
    res = g.get_project_by_name(project.name)

