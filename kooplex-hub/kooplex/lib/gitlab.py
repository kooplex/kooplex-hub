import json
import requests
from django.conf import settings
from threadlocals.threadlocals import get_current_request

from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient
from kooplex.lib.libbase import get_settings

class Gitlab(RestClient):
    """description of class"""

    SESSION_PRIVATE_TOKEN_KEY = 'gitlab_user_private_token'
    HEADER_PRIVATE_TOKEN_KEY = 'PRIVATE-TOKEN'
    URL_PRIVATE_TOKEN_KEY = 'private_token'

    base_url = get_settings('KOOPLEX_GITLAB', 'base_url', None, 'http://www.gitlab.com/')

    def __init__(self, request=None):
        self.request = request
        self.session = {}       # local session used for unit tests
    
    ###########################################################
    # HTTP reuqest authentication

    def get_session_store(self):
        if self.request:
            return self.request.session
        else:
            request = get_current_request()
        if request:
            return request.session
        else:
            return self.session

    def get_user_private_token(self):
        s = self.get_session_store()
        if Gitlab.SESSION_PRIVATE_TOKEN_KEY in s:
            return s[Gitlab.SESSION_PRIVATE_TOKEN_KEY]
        else:
            return None

    def set_user_private_token(self, user):
        s = self.get_session_store()
        s[Gitlab.SESSION_PRIVATE_TOKEN_KEY] = user[Gitlab.URL_PRIVATE_TOKEN_KEY]

    def http_prepare_url(self, url):
        return RestClient.join_path(Gitlab.base_url, url)

    def http_prepare_headers(self, headers):
        headers = RestClient.http_prepare_headers(self, headers)
        token = self.get_user_private_token()
        if token:
            headers[Gitlab.HEADER_PRIVATE_TOKEN_KEY] = token
        return headers

    ###########################################################
    # Django authentication hooks

    def authenticate(self, username=None, password=None):
        res = self.http_post("/session", params={'login': username, 'password': password})
        if res.status_code == 201:
            u = res.json()
            return res, u
        return res, None

    def get_user(self, username):
        return None

    def authenticate_user(self, username=None, password=None):
        res, user = self.authenticate(username, password)
        if user is not None:
            self.set_user_private_token(user)
            return res, user
        return res, None
    
    ###########################################################
    # Projects

    def get_projects(self):
        res = self.http_get('/projects')
        return res.json()