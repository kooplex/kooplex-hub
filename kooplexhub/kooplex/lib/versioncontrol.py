import requests
import requests.auth
import logging

from kooplex.settings import KOOPLEX

from .vc_github import list_projects as lp_gh
from .vc_gitlab import list_projects as lp_gl
from .vc_gitea import list_projects as lp_gt


logger = logging.getLogger(__name__)

def list_projects(vctoken):
    repository = vctoken.repository
    if repository.backend_type == repository.TP_GITHUB:
        return lp_gh(vctoken)
    elif repository.backend_type == repository.TP_GITLAB:
        return lp_gl(vctoken)
    elif repository.backend_type == repository.TP_GITEA:
        return lp_gt(vctoken)
    else:
        raise NotImplementedError("Unknown version control system type: %s" % vctoken.type)

def impersonator_clone(vcproject):
    url_base = KOOPLEX['impersonator'].get('base_url', 'http://localhost')
    A = requests.auth.HTTPBasicAuth(KOOPLEX['impersonator'].get('username'), KOOPLEX['impersonator'].get('password'))
    try:
        resp_echo = requests.get(url_base, auth = A)
    except ConnectionError:
        logger.critical('impersonator API is not running')
        raise
    params = {
        'clone': vcproject.project_ssh_url,
        'username': vcproject.token.user.username,
        'port': vcproject.token.repository.ssh_port,
        'prefix': vcproject.token.repository.backend_type,
        'rsa_file': '/home/{}/.ssh/{}'.format(vcproject.token.user.username, vcproject.token.fn_rsa), #TODO: store rsa keys automagically in a separate folder in cache volume (?)
            }
    url = '{}/api/versioncontrol/clone/{}'.format(url_base, vcproject.token.user.username)
    try:
        resp_info = requests.get(url, auth = A, params = params)
        rj = resp_info.json()
        if 'error' in rj:
            logger.warning('error to clone {} for user {} -- daemon response: {}'.format(vcproject, vcproject.token.user.username, rj))
            raise Exception(rj['error'])
        return rj['clone_folder']
    except Exception as e:
        logger.error('error to clone {} for user {} -- {}'.format(vcproject, vcproject.token.user.username, e))
        raise

def impersonator_removecache(vcproject):
    url_base = KOOPLEX['impersonator'].get('base_url', 'http://localhost')
    A = requests.auth.HTTPBasicAuth(KOOPLEX['impersonator'].get('username'), KOOPLEX['impersonator'].get('password'))
    try:
        resp_echo = requests.get(url_base, auth = A)
    except ConnectionError:
        logger.critical('impersonator API is not running')
        raise
    params = {
        'clone': vcproject.project_ssh_url,
        'username': vcproject.token.user.username,
        'prefix': vcproject.token.repository.backend_type,
            }
    url = '{}/api/versioncontrol/removecache/{}'.format(url_base, vcproject.token.user.username)
    try:
        resp_info = requests.get(url, auth = A, params = params)
        rj = resp_info.json()
        if 'error' in rj:
            logger.warning('error to clone {} for user {} -- daemon response: {}'.format(vcproject, vcproject.token.user.username, rj))
    except Exception as e:
        logger.error('error to clone {} for user {} -- {}'.format(vcproject, vcproject.token.user.username, e))

