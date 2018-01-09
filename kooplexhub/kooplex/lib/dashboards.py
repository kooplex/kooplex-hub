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
from kooplex.hub.models.dashboard_server import Dashboard_server
from kooplex.hub.models.project import Project

from kooplex.lib.debug import *
from html.parser import HTMLParser
import base64

DEBUG_LOCAL=True


def deploy(project_id, file, type, other_files=[]):
    print_debug("", DEBUG_LOCAL)
    from shutil import copyfile as cp
    from os import mkdir


    srv_dir = "/"
    project = Project.objects.get(id=project_id)
    D = Dashboard()
    g = Gitlab()
    creator = g.get_user_by_id(project.creator_id)
    D.creator_name = creator['username']
    if type == "dashboard":
        extradir = ipynb_file[:-6]

    dir_util.mkpath(D.dir_to)
    dir_from = os.path.join(srv_dir, project.owner_username, "projects", creator_name, project.name, file)

    if os.path.isdir(dir_from):
        1==1
        #dir_util.copy_tree(dir_from, D.dir_to)
    else:
        try:
            1==1
            #Err = copyfile(D.path_from, D.path_to)
        except  IOError:
            print_debug("ERROR: file cannot be written to %s" % destination)

         
def delete(self,path):
    print_debug("", DEBUG_LOCAL)
    url = "_api/notebooks/"
    url += "%s/" % path
    res = self.http_delete(url, )
#        if res.status_code != 404:
    message = res.json()
    return message


def clear_cache(self,path):
    print_debug("", DEBUG_LOCAL)
    url = "/_api/cache/"
    url += "%s/" % path
    res = self.http_delete(url, )
#        if res.status_code != 404:
    message = res.json()
    return message

def clear_cache_temp(self, cache_url):
    res = self.http_delete(cache_url)
    message = "OK"
    if res.status_code != 404 and res.status_code != 200:
      message = res.json()
    return message


#TODO

# CSS 
# /usr/local/lib/node_modules/jupyter-dashboards-server/public/css

#        Kernel Proxy
#	GET|POST|PUT|DELETE /api/*
#    Proxies Jupyter Kernel requests to the appropriate kernel gateway.
#    For execute_request messages, only a cell index is allowed in the code field. If actual code or non-numeric are specified, the entire message is not proxied to the kernel gateway.

def list_dashboards(self,request):
  gadmin = GitlabAdmin(request)
  projects = gadmin.get_all_projects()
  docli = Docker()
  prefix = get_settings('prefix', 'name')
  outer_host = get_settings('hub', 'outer_host')
  proto = get_settings('hub', 'protocol')
  list_of_dashboards = []
  for project in projects:
      if project['visibility']=="public":
          public=True
      variables = gadmin.get_project_variables(project['id'])
      for var in variables:
          if var['key'].rfind('dashboard_') > -1:
              image_name = var['value']
              image_type = image_name.split(prefix+"-notebook-")[1]
              name = prefix + "_dashboards-" + image_type
              dashboard_container = docli.get_container(name)
              dashboard_port=-1
              if dashboard_container:
                  ports=dashboard_container.ports
                  for P in ports:
                      if "PublicPort" in P.keys():
                          dashboard_port = P["PublicPort"]

              file = var['key'].split("dashboard_")[1]
              g = Gitlab()
              creator = g.get_user_by_id(project['creator_id'])
              creator_name = creator['username']
              url_ending ="%s/projects/%s/%s/%s/%s"% (project['owner']['username'], creator_name, project['name'], file,file)
              if dashboard_port>0:
                  url_to_file = "%s://%s/db/%d/dashboards/%s"% (proto, outer_host, dashboard_port, url_ending)
                  cache_url = "/db/%d/_api/cache/%s"% (dashboard_port, url_ending)
              else:
                  url_to_file = ""
                  cache_url = ""

              list_of_dashboards.append({'owner':project['owner']['username'],'name':project['name'],\
                'description': project['description'],'url': url_to_file, 'file': file, 'project_id':project['id'], 'public': public,\
                'cache_url': cache_url, 'image_type': image_type, 'creator_name' : creator_name, 'report_type': "dashboard"})


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
                                         'project_id':project['id'], 'public': project['public'], 'report_type': "html"})

      return list_of_dashboards

def deploy_html(self, imagename,username, owner, project_name, email, file):
    print_debug("",DEBUG_LOCAL)
    repo = Repo(username, name="")
    repo.commit_and_push(" %s as worksheet uploaded"%file, email, owner, project_name,[file],[])



def deploy_data(self, imagename, project, notebook_path_dir, file, extradir=''):
    from shutil import copyfile
    from distutils import dir_util

    print_debug("",DEBUG_LOCAL)
    sroot = get_settings('dashboards', 'base_dir', None, '')
    g = Gitlab()
    creator = g.get_user_by_id(project['creator_id'])
    creator_name = creator['username']
    path = os.path.join(sroot, imagename, project['owner']['username'], "projects", creator_name, project['name'], extradir)
    dir_util.mkpath(path)
    source = os.path.join(srv_dir, notebook_path_dir, file)
    destination = os.path.join(path, file)
    print("path", path)
    print("source", source, file)
    print("destination", destination)
    print("extradir", extradir)
    if os.path.isdir(source):
        dir_util.copy_tree(source, destination)
    else:
        try:
            Err = copyfile(source, destination)
        except  IOError:
            print_debug("ERROR: file cannot be written to %s" % destination)
            # return Err

def unpublish_html(self, id,file):
    g = Gitlab()
    res = g.delete_project_variable(id, "worksheet_%s" % file[:-5])
    print(res)



#FIXME: inconsistent file system structure
def unpublish_dashboard(self, id, image_type, username, creator_name, project_name, dirname):
    from distutils import dir_util
    file = dirname+".ipynb"
    g = Gitlab()
    g.delete_project_variable(id, "dashboard_%s" % file)

    sroot = get_settings('dashboards', 'base_dir', None, '')
    path = os.path.join(sroot, image_type, username, "projects", creator_name, project_name, dirname)
    Err = dir_util.remove_tree(path)
    print(Err)


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


