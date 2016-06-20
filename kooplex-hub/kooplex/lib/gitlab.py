import json
import requests
from django.conf import settings
from threadlocals.threadlocals import get_current_request
from importlib import import_module

class Gitlab:
    """description of class"""

    base_url = settings.GITLAB['base_url'] or 'http://www.gitlab.com/'

    admin_username = settings.GITLAB['admin_username'] or ''
    admin_password = settings.GITLAB['admin_password'] or ''
    admin_private_token = None

    def __init__(self, request=None):
        self.request = request
        return None
    
    def get_session_store(self):
        if self.request is not None:
            return self.request.session
        else:
            request = get_current_request()
            return request.session

    def get_user_private_token(self):
        s = self.get_session_store()
        return s['gitlab_user_private_token']

    def set_user_private_token(self, user):
        s = self.get_session_store()
        s['gitlab_user_private_token'] = user['private_token']

    def set_admin_private_token(self):
        if Gitlab.admin_private_token is None:
            self.authenticate_admin()
        return Gitlab.admin_private_token

    def http_prepare_url(self, url):
        return Gitlab.base_url + url

    def http_prepare_headers(self, headers=None, token=None):
        if headers is None:
            headers = {}
        if token is not None:
            headers['PRIVATE-TOKEN'] = token
        return headers

    def http_get(self, url, params=None, headers=None, token=None):
        headers = self.http_prepare_headers(headers, token)
        res = requests.get(self.http_prepare_url(url),
                           params= params,
                           headers= headers)
        return res

    def http_post(self, url, params=None, headers=None, data=None, token=None):
        headers = self.http_prepare_headers(headers, token)
        res = requests.post(self.http_prepare_url(url),
                            params= params,
                            headers= headers,
                            data=data)
        return res

    def authenticate(self, username=None, password=None):
        res = self.http_post("/session", params={'login': username, 'password': password})
        if res.status_code == 201:
            u = res.json()
            return res, u
        return res, None

    def authenticate_user(self, username=None, password=None):
        res, user = self.authenticate(username, password)
        if user is not None:
            self.set_user_private_token(user)
            return res, user
        return res, None

    def authenticate_admin(self):
        res, user = self.authenticate(admin_username, admin_password)
        if user is not None:
            Gitlab.admin_private_token = user['private_token']
        return res, user

    def create_user(self, user):
        # TODO: create external user in gitlab via REST API and set
        # identity to point to LDAP
        return None

    def get_user(self, username):
        return None

    def get_projects(self):
        token = self.get_user_private_token()
        res = self.http_get('/projects', token=token)
        return res.json()