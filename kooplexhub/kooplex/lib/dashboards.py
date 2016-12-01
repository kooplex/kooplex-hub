import json
import requests
from django.conf import settings
from threadlocals.threadlocals import get_current_request

from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient
from kooplex.lib.libbase import get_settings

from kooplex.lib.debug import *

DEBUG = True


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
        print_debug(DEBUG,"")
        return RestClient.join_path(Dashboards.base_url, url)

    def http_prepare_headers(self, headers):
        print_debug(DEBUG,"")
        headers = RestClient.http_prepare_headers(self, headers)
        token = Dashboards.DASHBOARD_SERVER_AUTH_TOKEN
        if token:
            headers[Dashboards.HEADER_PRIVATE_TOKEN_KEY] = token
        return headers

    def deploy(self,path,filename):
        print_debug(DEBUG, "")
        url = "http://172.20.0.21:3000/_api/notebooks/dashboards/"
        url += "%s/" % path
        #formdata=dict(file=filename)
        formdata = {'file': (filename, open(filename, 'r'))}
        res = self.http_post(url, formdata=formdata)
#        if res.status_code != 404:
        message = res.json()
        return message
        
#curl -X POST --header  "Authorization: notebook_to_dashboard_secret" "172.20.0.21:3000/_api/notebooks/dashboards/yyy"  -F file=@/srv/kooplex/compare/home/gitlabadmin/projects/gitlabadmin/readmes/index.ipynb
         
    def delete(self,path):
        print_debug(DEBUG, "")
        url = "_api/notebooks/"
        url += "%s/" % path
        res = self.http_delete(url, )
#        if res.status_code != 404:
        message = res.json()
        return message
        
        
    def clear_cached(self,path):
        print_debug(DEBUG, "")
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


    def list_dashboards(self):
      # Check whether we acces to it ?
      dashboards_dir = get_settings('dashboards', 'base_dir', None, '')
      
      #Get all projects, check for worksheetness
      for project in projects:
            variables=g.get_project_variable(project['id'],'worksheet')
       
      #Check whether they really exit or not
      list_of_existing_dashboards = []
      for d in list_of_dashboards:
       try:
        open(d,'r')
        list_of_existing_dashboards.append(d)
       except:
        pass
      return list_of_existing_dashboards
      