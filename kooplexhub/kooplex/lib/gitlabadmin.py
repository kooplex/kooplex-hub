import json
import requests
from django.conf import settings

from kooplex.lib.libbase import LibBase
from kooplex.lib.restclient import RestClient
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.libbase import get_settings

class GitlabAdmin(Gitlab):

    admin_username = get_settings('gitlab', 'admin_username', None, None)
    admin_password = get_settings('gitlab', 'admin_password', None, None)
    admin_private_token = None

    def http_prepare_headers(self, headers):
        headers = RestClient.http_prepare_headers(self, headers)
        token = get_admin_private_token()
        if token:
            headers['PRIVATE-TOKEN'] = token
        return headers

    def authenticate_admin(self):
        res, user = self.authenticate(admin_username, admin_password)
        if user is not None:
            Gitlab.admin_private_token = user['private_token']
        return res, user

    def get_admin_private_token(self):
        if Gitlab.admin_private_token is None:
            self.authenticate_admin()
        return Gitlab.admin_private_token

    ###########################################################
    # User management

    def create_user(self, user):
        # TODO: create external user in gitlab via REST API and set
        # identity to point to LDAP
        return None