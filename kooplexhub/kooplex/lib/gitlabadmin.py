"""
@author: Jozsef Steger, David Visontai
@summary: gitlab driver (access API with administrative privileges)
"""
import os
import json
import requests
import logging

from kooplex.lib.libbase import get_settings, keeptrying

logger = logging.getLogger(__name__)

class GitlabAdmin:
    base_url = get_settings('gitlab', 'base_url')

    def __init__(self, ):
        kw = {
            'url': os.path.join(self.base_url, 'session'),
            'params': { 'login': get_settings('gitlab', 'admin_username'), 'password': get_settings('gitlab', 'admin_password') },
        }
        response = keeptrying(requests.post, 3, **kw)
        logger.debug("response status: %d" % response.status_code)
        assert response.status_code == 201, response.json()
        self._session = response.json()
        self.token = self._session['private_token']
        logger.info('token retrieved')

    def create_user(self, user):
        name = "%s %s" % (user.first_name, user.last_name)
        kw = {
            'url': os.path.join(self.base_url, 'users'),
            'headers': { 'PRIVATE-TOKEN': self.token },
            'data': { 'name': name, 'username': user.username, 'email': user.email, 'bio': user.bio, 'confirm': False, 'password': user.password }
        }
        response = keeptrying(requests.post, 3, **kw)
        assert response.status_code == 201, response.json()
        information = response.json()
        logger.debug(information)
        return information

    def upload_userkey(self, user, key):
        kw = {
            'url': os.path.join(self.base_url, 'users', str(user.gitlab_id), 'keys'),
            'headers': { 'PRIVATE-TOKEN': self.token },
            'data': { 'title': 'gitlabkey', 'key': key.strip() }
        }
        response = keeptrying(requests.post, 3, **kw)
        assert response.status_code == 201, response.json()
        information = response.json()
        logger.debug(information)

    def delete_user(self, user):
        raise NotImplementedError


