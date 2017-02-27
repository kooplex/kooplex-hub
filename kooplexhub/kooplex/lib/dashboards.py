import json, os
import requests
from django.conf import settings
from threadlocals.threadlocals import get_current_request
from kooplex.lib.libbase import get_settings

from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient
from kooplex.lib.libbase import get_settings
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.lib.repo import Repo
from kooplex.lib.smartdocker import Docker

from kooplex.lib.debug import *
from html.parser import HTMLParser
import base64

DEBUG_LOCAL=True

class Dashboards(RestClient):
    """description of class"""

    DASHBOARD_SERVER_AUTH_TOKEN = 'notebook_to_dashboard_secret'
#    HEADER_PRIVATE_TOKEN_KEY = 'token'
    HEADER_PRIVATE_TOKEN_KEY = 'Authorization'
#    HEADER_PRIVATE_TOKEN_KEY = 'PRIVATE-TOKEN'
#    URL_PRIVATE_TOKEN_KEY = 'private_token'

    base_url = get_settings('dashboards', 'base_url', None, '')

    def __init__(self, request=None):
        self.request = request
        self.session = {}  # local session used for unit tests

        ###########################################################
        # HTTP request authentication

    def http_prepare_url(self, url):
        print_debug("",DEBUG_LOCAL)
        return RestClient.join_path(Dashboards.base_url, url)

    def http_prepare_headers(self, headers):
        print_debug("",DEBUG_LOCAL)
        headers = RestClient.http_prepare_headers(self, headers)
        token = Dashboards.DASHBOARD_SERVER_AUTH_TOKEN
        if token:
            headers[Dashboards.HEADER_PRIVATE_TOKEN_KEY] = token
        headers['Content-Type']='multipart/form-data'
#        headers['Content-Disposition']= 'form-data'
        return headers

    def deploy_api(self,path,filename):
        print_debug("", DEBUG_LOCAL)
        url = "_api/notebooks/"
#        url= ''
        url += "%s/" % path
        #formdata = {'file': open(filename,'rb').read()}
        #formdata = open(filename,'r')
#        formdata=dict(file=open(filename,'rb'))
        formdata=dict(file=open(filename,'rb').read())
#        formdata = {'file': open(filename,'rb'))}
        #formdata = {'file': filename}
        res = self.http_post(url, formdata=formdata)
#        if res.status_code != 404:
        message = res.json()

        return message
        
#curl -X POST --header  "Authorization: notebook_to_dashboard_secret" "172.20.0.21:3000/_api/notebooks/dashboards/yyy"  -F file=@/srv/kooplex/compare/home/gitlabadmin/projects/gitlabadmin/readmes/index.ipynb
         
    def deploy(self,username, owner, project_name, file):
        print_debug("", DEBUG_LOCAL)
        from shutil import copyfile as cp
        from os import mkdir
        path = get_settings('dashboards', 'base_dir', None, '')
        for det in [username, owner, project_name]:
          path = LibBase.join_path(path,det)
          try:
            mkdir(path)
          except FileExistsError:
            pass
        
        filename = file[file.rfind("/")+1:]
        path = LibBase.join_path(path, filename)
        print(file,filename,path)
        try:
          Err = cp(file,path)
        except  IOError: 
          print_debug( "ERROR: file cannot be written to %s"%path)
          #return Err         
         
    def delete(self,path):
        print_debug("", DEBUG_LOCAL)
        url = "_api/notebooks/"
        url += "%s/" % path
        res = self.http_delete(url, )
#        if res.status_code != 404:
        message = res.json()
        return message
        
        
    def clear_cached(self,path):
        print_debug("", DEBUG_LOCAL)
        url = "/_api/cache/"
        url += "%s/" % path
        res = self.http_delete(url, )
#        if res.status_code != 404:
        message = res.json()
        return message

#TODO

# CSS 
# /usr/local/lib/node_modules/jupyter-dashboards-server/public/css
        
#        Kernel Proxy
#	GET|POST|PUT|DELETE /api/*
#    Proxies Jupyter Kernel requests to the appropriate kernel gateway.
#    For execute_request messages, only a cell index is allowed in the code field. If actual code or non-numeric are specified, the entire message is not proxied to the kernel gateway.
    def find_dashboard_server(self, image):
        docli = Docker()
        all_containers = docli.list_containers()
        for container in all_containers:
            container_name = container['Names'][0]
            if container_name.rfind("dashboards-") > -1:
                if container_name.split("dashboards-")[1] == image.split("kooplex-notebook-")[1]:
                    for P in container['Ports']:
                        if "PublicPort" in P.keys():
                            port = P["PublicPort"]
                            return container_name, port

    def list_dashboards(self,request):
      gadmin = GitlabAdmin(request)
      projects = gadmin.get_all_projects()
      list_of_dashboards = []
      for project in projects:
          variables = gadmin.get_project_variables(project['id'])
          for var in variables:
              if var['key'].rfind('dashboard_') > -1:
                  image_name = var['value']
                  name, port = self.find_dashboard_server(image_name)
                  file = var['key'].split("dashboard_")[1]
                  url_to_file = get_settings('dashboards', 'base_url')
                  if url_to_file[-1]=="/":
                      url_to_file=url_to_file[:-1]
                  url_to_file += ":%d/%d/%d/%s/%s"%(port,project['owner']['id'],project['creator_id'],project['name'],file)

                  list_of_dashboards.append({'owner':project['owner']['username'],'name':project['name'],\
                    'description': project['description'],'url': url_to_file, 'file': file, 'project_id':project['id']})

      return list_of_dashboards

    def list_reports_html(self, request):
          # Get all projects, check for worksheetness
          gadmin = GitlabAdmin(request)
          projects = gadmin.get_all_projects()
          list_of_dashboards = []
          for project in projects:
              variables = gadmin.get_project_variables(project['id'])
              for var in variables:
                  if var['key'].rfind('worksheet_')>-1 and var['value'].rfind('html')>-1:
                      file = var['value']
                      file_vmi = gadmin.get_file(project['id'], file)
                      html_content = base64.b64decode(file_vmi['content'])
                      first_image = Find_first_img_inhtml(html_content.decode('utf-8'))
                      list_of_dashboards.append({'owner': project['owner']['username'], 'name': project['name'], \
                                             'description': project['description'], 'picture': first_image,'file':file, \
                                             'project_id':project['id']})

          return list_of_dashboards

    def deploy_html(self, username, owner, project_name, email, notebook_path_dir, file):
        print_debug("",DEBUG_LOCAL)
        from shutil import copyfile as cp
        from os import mkdir
        path = get_settings('dashboards', 'base_dir', None, '')
        srv_dir = get_settings('users', 'srv_dir')
        for det in [username, owner, project_name]:
            path = LibBase.join_path(path, det)
            try:
                mkdir(path)
            except FileExistsError:
                pass

        repo = Repo(username, owner + "/" + project_name)
        repo.commit_and_push(" %s as worksheet uploaded"%file, email, owner, project_name,[file],[])
        fromfile = LibBase.join_path(srv_dir, notebook_path_dir)
        fromfile = LibBase.join_path(fromfile, file)
        tofile = LibBase.join_path(path, file)
        print(file, fromfile, tofile)
        try:
            #Err = cp(fromfile, tofile)
            Err = os.remove(fromfile)
        except  IOError:
            print_debug("ERROR: file cannot be written to %s" % tofile)
            # return Err

    def deploy_data(self, project, notebook_path_dir, file):
        print_debug("",DEBUG_LOCAL)
        from shutil import copyfile as cp
        from os import mkdir
        path = get_settings('dashboards', 'base_dir', None, '')
        srv_dir = get_settings('users', 'srv_dir')
        for det in [str(project['owner']['id']),str(project['creator_id']),project['name']]:
            path = LibBase.join_path(path, det)
            try:
                mkdir(path)
            except FileExistsError:
                pass

        fromfile = LibBase.join_path(srv_dir, notebook_path_dir)
        fromfile = LibBase.join_path(fromfile, file)
        tofile = LibBase.join_path(path, file)
        print(file, fromfile, tofile)
        try:
            Err = cp(fromfile, tofile)
        except  IOError:
            print_debug("ERROR: file cannot be written to %s" % tofile)
            # return Err

    def unpublish(self, id,project,file):
        g = Gitlab()
        if file[-4:] == "html":
            g.delete_project_variable(id, "worksheet_%s" % file[:-5])
        else:
            file += ".ipynb"
            path = get_settings('dashboards', 'base_dir', None, '')
            file_to_delete = path + "%d/%d/%s/%s"%(project['owner']['id'],project['creator_id'],project['name'],file)
            Err = os.remove(file_to_delete)
            g.delete_project_variable(id, "dashboard_%s" % file)


    def unpublish_dashboard(self, id, name, file):
        path = get_settings('dashboards', 'base_dir', None, '')
        g = Gitlab()
        dsd
        if file[-4:] == "html":
            g.delete_project_variable(id, "worksheet_%s" % file[:-5])

        else:
            file += ".ipynb"
            file_to_delete = LibBase.join_path(path, username)
            file_to_delete = LibBase.join_path(file_to_delete, owner)
            file_to_delete = LibBase.join_path(file_to_delete, name)
            file_to_delete = LibBase.join_path(file_to_delete, file)
            g.delete_project_variable(id, "dashboard_%s" % file)
            Err = os.remove(file_to_delete)


def Find_first_img_inhtml(content):
        class MyHTMLParser(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "img":
                    raise Exception('img', attrs[0][1])

        parser = MyHTMLParser()
        try:
            parser.feed(content)
        except Exception as inst:
            return(inst.args[1])


