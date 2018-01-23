"""
@author: Jozsef Steger, David Visontai
@summary: gitlab driver
"""
import os
import json
import requests
import logging

from kooplex.lib.libbase import get_settings, keeptrying

logger = logging.getLogger(__name__)

class Gitlab:
    base_url = get_settings('gitlab', 'base_url')

    def __init__(self, user):
        kw = {
            'url': os.path.join(self.base_url, 'session'),
            'params': { 'login': user.username, 'password': user.password },
        }
        response = keeptrying(requests.post, 3, **kw)
        logger.debug("response status: %d" % response.status_code)
        assert response.status_code == 201, response.json()
        self._session = response.json()
        self.token = self._session['private_token']
        logger.info('token retrieved')

    @property
    def gitlab_id(self):
        return self._session['id']

    def create_project(self, project):
        from .libbase import bash
        kw = {
            'url': os.path.join(self.base_url, 'projects'),
            'headers': { 'PRIVATE-TOKEN': self.token },
            'data': { 'name': project.name, 'visibility': project.scope.name, 'description': project.description }
        }
        response = keeptrying(requests.post, 3, **kw)
        assert response.status_code == 201, response.json()
        information = response.json()
        logger.debug(information)
        gitlab_id = information['id']
        project.gitlab_id = gitlab_id
        logger.info('created project %s -> gitlab project id: %d' % (project, gitlab_id))
        self.patch_notification(gitlab_id)
        self.create_project_file(gitlab_id)
        return information

    def delete_project(self, project):
        kw = {
            'url': os.path.join(self.base_url, 'projects', str(project.gitlab_id)),
            'headers': { 'PRIVATE-TOKEN': self.token },
        }
        response = keeptrying(requests.delete, 3, **kw)
        information = response.json()
        statuscode = response.status_code
        assert statuscode in [ 201, 404 ], information
        if statuscode == 201:
            logger.info('deleted project %s (gitlab project id: %d)' % (project, project.gitlab_id))
        elif statuscode == 404:
            logger.warning('not found project %s (gitlab project id: %d)' % (project, project.gitlab_id))
        return information

    def add_project_members(self, project, user):
        kw = {
            'url': os.path.join(self.base_url, 'projects', str(project.gitlab_id), 'members'),
            'headers': { 'PRIVATE-TOKEN': self.token },
            'data': { 'user_id': user.gitlab_id, 'access_level': 40 }
        }
        response = keeptrying(requests.post, 3, **kw)
        assert response.status_code == 201, response.json()
        logger.info('user %s added to project %s' % (user, project))
        self.patch_notification(gitlab_id)
        return response.json()

    def delete_project_members(self,project_id, user_id):
        kw = {
            'url': os.path.join(self.base_url, 'projects', str(project.gitlab_id), 'members', str(user.gitlab_id)),
            'headers': { 'PRIVATE-TOKEN': self.token },
        }
        response = keeptrying(requests.delete, 3, **kw)
        assert response.status_code == 201, response.json()
        logger.info('user %s deleted from project %s' % (user, project))
        return response.json()

    def create_project_file(self, gitlab_id, filename = "README.md", content = "* proba", commit_message = "Created a default README.md file"):
        kw = {
            'url': os.path.join(self.base_url, 'projects', str(gitlab_id), 'repository', 'files', filename),
            'headers': { 'PRIVATE-TOKEN': self.token },
            'data': { 'branch': 'master', 'content': content, 'commit_message': commit_message }
        }
        response = keeptrying(requests.post, 3, **kw)
#        assert response.status_code == 404, response.json()
        logger.info('file %s created and committed to %d' % (filename, gitlab_id))
        return response.json()

    def patch_notification(self, gitlab_id):
        hostname_gitlabdb = get_settings('gitlabdb', 'hostname')
        db_passwd = get_settings('gitlabdb', 'db_password')
        db_port = get_settings('gitlabdb', 'psql_port')
        command = "PGPASSWORD={0} psql -h {1} -p {2} -U postgres -d gitlabhq_production -c 'update notification_settings set level=2 where source_id={3};'\"".format(db_passwd, hostname_gitlabdb, db_port, gitlab_id)
        logger.debug('patched %d' % gitlab_id)

    def get_repository_commits(self, project):
        def extract_info(record):
            keep_tags = [ 'id', 'committer_name', 'title', 'committed_date' ]
            parent_ids = record['parent_ids']
#            assert len(parent_ids) < 2, "More than one parent commit"
            R = dict(map(lambda x: (x, record[x]), keep_tags))
            R['parent_id'] = parent_ids[0] if len(parent_ids) else None
            return R

        kw = {
            'url': os.path.join(self.base_url, 'projects', str(project.gitlab_id), 'repository', 'commits'),
            'headers': { 'PRIVATE-TOKEN': self.token },
        }
        response = keeptrying(requests.get, 3, **kw)
        assert response.status_code != 404, response.json()
        logger.debug('commit msgs for project %s' % project)
        response_list = response.json()
        commited_chain = []
        latest = None
        end = False
        while not end:
           for i in response_list:
               if latest is None or i['id'] == latest['parent_id']:
                   response_list.remove(i)
                   latest = extract_info(i)
                   commited_chain.append(latest)
               if latest['parent_id'] is None:
                   end = True
                   break
        return commited_chain

