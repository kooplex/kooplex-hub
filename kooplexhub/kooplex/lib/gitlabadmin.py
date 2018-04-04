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
    api_url = os.path.join(get_settings('gitlab', 'base_url'), get_settings('gitlab', 'api_path'))

    def __init__(self, ):
        kw = {
            'url': os.path.join(self.base_url, 'oauth/token'),
            'params': { 'login': get_settings('gitlab', 'admin_username'), 'password': get_settings('gitlab', 'admin_password') },
        }
        response = keeptrying(requests.post, 3, **kw)
        logger.debug("response status: %d" % response.status_code)
        assert response.status_code == 200, response.json()
        self._session = response.json()
        self.token = self._session['access_token']
        logger.info('token retrieved')

    def create_user(self, user):
        name = "%s %s" % (user.first_name, user.last_name)
        kw = {
            'url': os.path.join(self.api_url, 'users'),
            'headers': { 'Authorization': "Bearer %s" % self.token },
            'data': { 'name': name, 'username': user.username, 'email': user.email, 'bio': user.bio, 'skip_confirmation': True, 'password': user.password }
        }
        response = keeptrying(requests.post, 3, **kw)
        assert response.status_code == 201, response.json()
        information = response.json()
        logger.debug(information)
        return information

    def upload_userkey(self, user, key):
        kw = {
            'url': os.path.join(self.api_url, 'users', str(user.gitlab_id), 'keys'),
            'headers': { 'Authorization': "Bearer %s" % self.token },
            'data': { 'title': 'gitlabkey', 'key': key.strip() }
        }
        response = keeptrying(requests.post, 3, **kw)
        assert response.status_code == 201, response.json()
        information = response.json()
        logger.debug(information)

    def delete_user(self, user):
        if user.gitlab_id is None:
            logger.error("User %s does not have a valid gitlab_id, cannot remove the account" % user)
            return
        kw = {
            'url': os.path.join(self.api_url, 'users', str(user.gitlab_id)),
            'headers': { 'Authorization': "Bearer %s" % self.token },
            'data': { 'hard_delete': True }
        }
        response = keeptrying(requests.delete, 3, **kw)
        assert response.status_code == 201, response.json()
        information = response.json()
        logger.debug(information)

