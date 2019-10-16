import requests
import requests.auth
import logging

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
    url_base = 'http://kooplex-test-impersonator:5000'
    A = requests.auth.HTTPBasicAuth('hub', 'blabla')
    try:
        resp_echo = requests.get(url_base, auth = A)
    except ConnectionError:
        logger.critical('impersonator API is not running')
        raise
    rs = vcproject.repository #FIXME: modify model!!!
    port = 222
    srv = rs.split('/')[-2]
    be = 'gitea'
    params = {
        'server': srv,
        'port': 222,
        'project': vcproject.project_name,
        'prefix': be, 
        'username': vcproject.token.user.username,
            }
    url = '{}/api/versioncontrol/clone'.format(url_base)
    try:
        resp_info = requests.get(url, auth = A, params = params)
        rj = resp_info.json()
        if 'error' in rj:
            logger.warning('error to clone {} for user {} -- daemon response: {}'.format(vcproject, vcproject.token.user.username, rj))
    except Exception as e:
        logger.error('error to clone {} for user {} -- {}'.format(vcproject, vcproject.token.user.username, e))

def impersonator_removecache(vcproject):
    url_base = 'http://kooplex-test-impersonator:5000'
    A = requests.auth.HTTPBasicAuth('hub', 'blabla')
    try:
        resp_echo = requests.get(url_base, auth = A)
    except ConnectionError:
        logger.critical('impersonator API is not running')
        raise
    url = '{}/api/versioncontrol/removecache/{}/{}'.format(url_base, vcproject.token.user.username, vcproject.project_name.split('/')[-1]) #FIXME: api signature not complete
    try:
        resp_info = requests.get(url, auth = A)
        rj = resp_info.json()
        if 'error' in rj:
            logger.warning('error to clone {} for user {} -- daemon response: {}'.format(vcproject, vcproject.token.user.username, rj))
    except Exception as e:
        logger.error('error to clone {} for user {} -- {}'.format(vcproject, vcproject.token.user.username, e))

