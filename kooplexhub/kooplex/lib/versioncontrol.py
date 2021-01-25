import requests
import requests.auth
import logging
import pickle
import base64

from kooplex.settings import KOOPLEX

from .vc_github import test_token as testtoken_gh, list_projects as lp_gh, upload_rsa as up_gh
from .vc_gitlab import list_projects as lp_gl
from .vc_gitea import test_token as testtoken_gt, list_projects as lp_gt, upload_rsa as up_gt


logger = logging.getLogger(__name__)

def log_decorator(msg):
    def inner(func):
        def wrapper(vctoken):
            func(vctoken)
            logger.info(msg.format(vctoken = vctoken))
        return wrapper
    return inner


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

@log_decorator('Public RSA key added to {vctoken.repository.url} for user {vctoken.user}')
def upload_rsa(vctoken):
    repository = vctoken.repository
    if repository.backend_type == repository.TP_GITEA:
        return up_gt(vctoken)
    elif repository.backend_type == repository.TP_GITHUB:
        return up_gh(vctoken)
   # elif repository.backend_type == repository.TP_GITLAB:
   #     return lp_gl(vctoken)
    else:
        raise NotImplementedError("Unknown version control system type: %s" % vctoken.type)

@log_decorator('User token match at {vctoken.repository.url} for user {vctoken.user}')
def test_token(vctoken):
    repository = vctoken.repository
    if repository.backend_type == repository.TP_GITEA:
        return testtoken_gt(vctoken)
    elif repository.backend_type == repository.TP_GITHUB:
        return testtoken_gh(vctoken)
   # elif repository.backend_type == repository.TP_GITLAB:
   #     return lp_gl(vctoken)
    else:
        raise NotImplementedError("Unknown version control system type: %s" % vctoken.type)

def impersonator_repo(vcproject, do):
    url_base = KOOPLEX['impersonator'].get('base_url', 'http://localhost')
    A = requests.auth.HTTPBasicAuth(KOOPLEX['impersonator'].get('username'), KOOPLEX['impersonator'].get('password'))
    try:
        resp_echo = requests.get(url_base, auth = A)
    except ConnectionError:
        logger.critical('impersonator API is not running')
        raise
    data_dict = {
            'url_clone_repo': vcproject.project_ssh_url,
            'service_url': vcproject.token.repository.url, 
            'username': vcproject.token.user.username,
            'rsa': vcproject.token.rsa,
            'do': do
            }
    data = base64.b64encode(pickle.dumps(data_dict, protocol = 2))
    url = f'{url_base}/api/versioncontrol/{data}'
    try:
        assert do in [ 'clone', 'drop' ], f'Wrong command {do}'
        resp_info = requests.get(url, auth = A)
        rj = resp_info.json()
        if 'error' in rj:
            logger.warning(f'error to {do} repomanage of {vcproject.project_ssh_url} for user {vcproject.token.user.username} -- daemon response: {rj}')
            raise Exception(rj['error'])
        return rj.get('clone_folder', None) #FIXME: rename repo_folder
    except Exception as e:
        logger.error(f'error to {do} repomanage of {vcproject.project_ssh_url} for user {vcproject.token.user.username}')

