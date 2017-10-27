import json
import base64
import requests
import subprocess, shlex
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
        self.api_version = "api/v4"
    
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
        print("HEADERS",headers)
        return headers

    ###########################################################
    # Django authentication hooks

    def authenticate(self, username=None, password=None):
        print_debug("",DEBUG_LOCAL)
        res = self.http_post(self.api_version+"/session", params={'login': username, 'password': password})
        if res.status_code == 201:
            u = res.json()
            return res, u
        return res, None

    def get_user(self,username):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/users?username=%s'%username)
        return res.json()

    def get_user_by_id(self,id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/users/%d'%id)
        return res.json()

    def get_alluser(self):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/users')
        return res

    def get_project(self, project_id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/projects/%s'%project_id)
        project_json = res.json()
        if 'message' in project_json:
            raise ValueError("MESSAGE: %s"%(projects_json['message']))
        return project_json

    def get_project_by_name(self,project_name):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/projects?search=%s'%project_name)
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
        res = self.http_get(self.api_version+'/projects')
        print_debug("ITT")
        print(res)
        projects_json = res.json()
        unforkable_projectids = self.get_unforkable_projectids(projects_json)
        return projects_json, unforkable_projectids

    def get_my_projects(self):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/projects?membership=true')
        print_debug("ITT")
        print(res)
        projects_json = res.json()
        return projects_json

    def get_unforkable_projectids(self, projects_json):
        print_debug("",DEBUG_LOCAL)
        result = set()
        for project in projects_json:
            if 'forked_from_project' in project:
                result.add(project['forked_from_project']['id'])
        return result

    def get_project_variables(self,project_id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v4/projects/%d/variables'%(project_id))
        project_variables = res.json()
        return project_variables

    def get_project_variable(self,project_id, key):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v4/projects/%s/variables/%s'%(project_id, key))
        variable = res.json()
        if 'value' in variable:
          return variable['value']
        else:
          return None

    def get_project_members(self,id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get(self.api_version+'/projects/%s/members'%str(id))
        return res.json()

    def add_project_members(self,project_id, user_id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_post(self.api_version+'/projects/%d/members?user_id=%d&access_level=40'%(project_id, user_id))
        self.patch_notification(project_id)
        return res.json()

    def set_project_visibility(self,project_id, level):
        print_debug("",DEBUG_LOCAL)
        data = {
            'visibility': level,
        }
        res = self.http_put(self.api_version+'/projects/%s'%project_id, params=data)
        return res.json()

    def delete_project_members(self,project_id, user_id):
        print_debug("",DEBUG_LOCAL)
        res = self.http_delete(self.api_version+'/projects/%d/members/%d'%(project_id, user_id))
        return res.json()

    def get_file(self,project_id,file):
        print_debug("",DEBUG_LOCAL)
        res = self.http_get('api/v4/projects/%s/repository/files?file_path=%s&ref=master'%(project_id,file))
        return res.json()


    def fork_project(self, itemid):
        print_debug("",DEBUG_LOCAL)
        res = self.http_post("api/v4/projects/fork/" + itemid)
        message = ""
        if res.status_code == 409:
            message = res.json()["message"]["base"][0]
        return message

    def create_mergerequest(self, project_id, target_id, title, description):
        print_debug("",DEBUG_LOCAL)
        url = "api/v4/projects/"
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
        url = "api/v4/projects/"
        url += itemid
        url += "/merge_requests?state=opened"
        res = self.http_get(url)
        return res.json()

    def accept_mergerequest(self, project_id, mergerequestid):
        print_debug("",DEBUG_LOCAL)
        url = self.api_version+"/projects/%d" % project_id
        url += "/merge_requests/" + mergerequestid
        url += "/merge"
        res = self.http_put(url)
        message = ""
        if res.status_code != 200:
            message = res.json()
        return message

    def patch_notification(self, pid):
        prefix = get_settings('prefix', 'name')
        containername=prefix+"-gitlabdb"
        db_passwd = get_settings('gitlabdb', 'db_password')
        command="bash -c \"PGPASSWORD={0} psql -h {1} -p 5432 -U postgres -d gitlabhq_production -c 'update notification_settings set level=2 where source_id={2};'\"".format(db_passwd,containername,pid)
        subprocess.call(shlex.split(command))
        
    def create_project(self,project_name,public='false',description=""):
        print_debug("",DEBUG_LOCAL)
        url = self.api_version+"/projects"
        url += "?name=%s&visibility=%s&description=%s" % (project_name, public, description)
        res = self.http_post(url)
        message = ""
        if res.status_code != 201:
            message = res.json()
        # set project level notification to watch
        pid = self.get_project_by_name(project_name)[0]['id']
        #url = self.api_version+"/projects/%(id)d/notification_settings?level=watch" % res[0]
        #res = self.http_post(url)   # NOTE: failure is not handled, silently ignored
        self.patch_notification(pid)
        return message

    def delete_project(self, project_id):
        print_debug("",DEBUG_LOCAL)
        url = self.api_version+"/projects/%s"% project_id
        res = self.http_delete(url)
        message = ""
        if res.status_code != 201:
            message = res.json()
        return message

    def create_project_variable(self,project_id,key,value):
        print_debug("",DEBUG_LOCAL)
        url = self.api_version+"/projects/"
        url += "%s"%str(project_id)
        url += "/variables"
        data = dict(key=key, value=value)
        res = self.http_post(url,params=data)
        if res.status_code != 404:
            message = res.json()
        return message

    def create_project_readme(self,project_id,file,content,commitmsg):
        print_debug("",DEBUG_LOCAL)
        url = self.api_version+"/projects/"
        url += "%d"%project_id
        url += "/repository/files/"
        url += "%s?branch=master&content=%s&commit_message=%s"%(file, content, commitmsg)
        res = self.http_post(url)
        print(res)
        if res.status_code != 404:
            message = res.json()
        return message
        
    #def ensure_variable_exists(self, project_id, key, value):
    #    url = self.api_version+"/projects/"
    #    url += "%s" % project_id
    #    url += "/variables/%s" % key
    #    data = dict(value=value)

    def change_variable_value(self,project_id,key,value):
        print_debug("",DEBUG_LOCAL)
        url = self.api_version+"/projects/"
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
        url = self.api_version+"/projects/"
        url += "%s"%project_id
        url += "/variables/%s"%key
        res = self.http_delete(url)
        if res.status_code != 404:
            return res.json()
        else:
            return "404"




    def get_repository_commits(self,project_id):
        def extract_info(record):
            keep_tags = [ 'id', 'committer_name', 'title', 'committed_date' ]
            parent_ids = record['parent_ids']
#            assert len(parent_ids) < 2, "More than one parent commit"
            R = dict(map(lambda x: (x, record[x]), keep_tags))
            R['parent_id'] = parent_ids[0] if len(parent_ids) else None
            return R

        print_debug("",DEBUG_LOCAL)
        url = self.api_version + "/projects/%s/repository/commits" % str(project_id)
        res = self.http_get(url)
        assert res.status_code != 404
        resp_list = res.json()
        commited_chain = []
        latest = None
        end = False
        while not end:
           for i in resp_list:
               if latest is None or i['id'] == latest['parent_id']:
                   resp_list.remove(i)
                   latest = extract_info(i)
                   commited_chain.append(latest)
               if latest['parent_id'] is None:
                   end = True
                   break
        return commited_chain
