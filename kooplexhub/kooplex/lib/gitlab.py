import json
import base64
import requests
from django.conf import settings
from threadlocals.threadlocals import get_current_request

from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient
from kooplex.lib.libbase import get_settings

from kooplex.lib.debug import *

DEBUG_LOCAL=False

class Gitlab(RestClient):
    """description of class"""

    SESSION_PRIVATE_TOKEN_KEY = 'gitlab_user_private_token'
    HEADER_PRIVATE_TOKEN_KEY = 'PRIVATE-TOKEN'
    URL_PRIVATE_TOKEN_KEY = 'private_token'

    base_url = get_settings('gitlab', 'base_url', None, 'http://www.gitlab.com/')

    def __init__(self, request=None):
        self.request = request
        self.session = {}       # local session used for unit tests
    
    ###########################################################
    # HTTP request authentication

    def get_session_store(self):
        print_debug("",DEBUG_LOCAL)
        if self.request:
            return self.request.session
        else:
            request = get_current_request()
        if request:
            return request.session
        else:
            return self.session

    def get_user_private_token(self):
        print_debug("",DEBUG_LOCAL)
        s = self.get_session_store()
        if Gitlab.SESSION_PRIVATE_TOKEN_KEY in s:
            return s[Gitlab.SESSION_PRIVATE_TOKEN_KEY]
        else:
            return None

    def set_user_private_token(self, user):
        print_debug("",DEBUG_LOCAL)
        s = self.get_session_store()
        s[Gitlab.SESSION_PRIVATE_TOKEN_KEY] = user[Gitlab.URL_PRIVATE_TOKEN_KEY]

    def http_prepare_url(self, url):
        print_debug("",DEBUG_LOCAL)
        return RestClient.join_path(Gitlab.base_url, url)

    def http_prepare_headers(self, headers):
        print_debug("",DEBUG_LOCAL)
        headers = RestClient.http_prepare_headers(self, headers)
        token = self.get_user_private_token()
        if token:
            headers[Gitlab.HEADER_PRIVATE_TOKEN_KEY] = token
        return headers

    ###########################################################
    # Django authentication hooks

    def authenticate(self, username=None, password=None):
        print_debug("",DEBUG_LOCAL)
        res = self.http_post("api/v3/session", params={'login': username, 'password': password})
        if res.status_code == 201:
            u = res.json()
            return res, u
        return res, None

    def get_user(self,username):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v3/users?username=%s'%username)
        return res.json()
    
    def get_alluser(self):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v3/users')
        return res

    def get_project_by_name(self,project_name):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v3/projects/search/%s'%project_name)
        return res.json()

    def authenticate_user(self, username=None, password=None):
        print_debug("",DEBUG_LOCAL)
        res, user = self.authenticate(username, password)
        if user is not None:
            self.set_user_private_token(user)
            return res, user
        return res, None
    
    ###########################################################
    # Projects

    def get_projects(self):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v3/projects')
        #print(res)
        projects_json = res.json()
        unforkable_projectids = self.get_unforkable_projectids(projects_json)
        return projects_json, unforkable_projectids

    def get_unforkable_projectids(self, projects_json):
        print_debug("",DEBUG_LOCAL)
        result = set()
        for project in projects_json:
            if 'forked_from_project' in project:
                result.add(project['forked_from_project']['id'])
        return result

    def get_project_variables(self,project_id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v3/projects/%d/variables'%(project_id))
        project_variables = res.json()
        return project_variables

    def get_project_variable(self,project_id, key):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v3/projects/%s/variables/%s'%(project_id, key))
        variable = res.json()
        if 'value' in variable:
          return variable['value']
        else:
          return None

    def get_file(self,project_id,file):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v3/projects/%s/repository/files?file_path=%s&ref=master'%(project_id,file))
        return res.json()


    def fork_project(self, itemid):
        print_debug("",DEBUG_LOCAL)
        res = self.http_post("api/v3/projects/fork/" + itemid)
        message = ""
        if res.status_code == 409:
            message = res.json()["message"]["base"][0]
        return message

    def create_mergerequest(self, project_id, target_id, title, description):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/"
        url += project_id
        url += "/merge_requests?source_branch=master&target_branch=master"
        url += "&target_project_id=" + target_id
        url += "&title=" + title
        url += "&description=" + description
        res = self.http_post(url)
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def list_mergerequests(self, itemid):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/"
        url += itemid
        url += "/merge_requests?state=opened"
        res = self.http_get(url)
        return res.json()

    def accept_mergerequest(self, project_id, mergerequestid):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/"
        url += project_id
        url += "/merge_requests/"
        url += mergerequestid
        url += "/merge"
        res = self.http_put(url)
        message = ""
        if res.status_code != 200:
            message = res.json()
        return message

    def create_project(self,project_name,public='false',description=""):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects"
        url += "?name=%s"%project_name
        url += "&public=%s"%public
        url += "&description=%s"%description
        res = self.http_post(url)
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def delete_project(self, project_id):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/%s"% project_id
        res = self.http_delete(url)
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def create_project_variable(self,project_id,key,value):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/"
        url += "%s"%str(project_id)
        url += "/variables"
        data = dict(key=key, value=value)
        res = self.http_post(url,params=data)
        if res.status_code != 404:
            message = res.json()
        return message

    def create_project_readme(self,project_id,file,content,commitmsg):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/"
        url += "%d"%project_id
        url += "/repository/files"
#        url += "?file_path=app/project.rb&branch_name=master&author_email=author%40example.com&author_name=Firstname%20Lastname&content=some%20content&commit_message=create%20a%20new%20file
        url += "?file_path=%s"%file
        url += "&branch_name=master&content=%s"%content
        url += "&commit_message=%s"%commitmsg
        res = self.http_post(url)
        print(res)
        if res.status_code != 404:
            message = res.json()
        return message
        
    #def ensure_variable_exists(self, project_id, key, value):
    #    url = "api/v3/projects/"
    #    url += "%s" % project_id
    #    url += "/variables/%s" % key
    #    data = dict(value=value)

    def change_variable_value(self,project_id,key,value):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/"
        url += "%s"%project_id
        url += "/variables"
        data = dict(value=value)
        #Check first whether it exists
        res = self.http_put(url+"/%s"% key, params=data)
        if res.status_code != 404:
            message = res.json()
        else:
            #if it doesn't exist, then create it
            data = dict(key=key, value=value)
            res = self.http_post(url, params=data)
            if res.status_code != 404:
                message = res.json()

        return message

    def delete_project_variable(self,project_id,key):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/"
        url += "%s"%project_id
        url += "/variables/%s"%key
        res = self.http_delete(url)
        if res.status_code != 404:
            return res.json()
        else:
            return "404"




    def get_repository_commits(self,project_id):
        print_debug("",DEBUG_LOCAL)
        url = "api/v3/projects/"
        url += "%s/repository/commits"%str(project_id)
        res = self.http_get(url)
        if res.status_code != 404:
            message = res.json()
        return message
