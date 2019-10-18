import logging
import seafileapi
import requests
import requests.auth

from kooplex.settings import KOOPLEX

logger = logging.getLogger(__name__)

def list_libraries(fstoken):
    syncserver = fstoken.syncserver
    if syncserver.backend_type == syncserver.TP_SEAFILE:
        client = seafileapi.connect(syncserver.url, fstoken.user.username, fstoken.token, None)
        for r in client.repos.list_repos():
            yield r
    else:
        raise NotImplementedError("Unknown version control system type: %s" % fstoken.type)

def seafilepw_update(username, password):
    A = requests.auth.HTTPBasicAuth(KOOPLEX['impersonator'].get('username'), KOOPLEX['impersonator'].get('password'))
    requests.get('{}/api/setpass/{}/{}'.format(KOOPLEX['impersonator'].get('seafile_api', 'http://localhost'), username, password), auth = A)

def impersonator_sync(library, start):
    url_base = KOOPLEX['impersonator'].get('base_url', 'http://localhost')
    A = requests.auth.HTTPBasicAuth(KOOPLEX['impersonator'].get('username'), KOOPLEX['impersonator'].get('password'))
    try:
        resp_echo = requests.get(url_base, auth = A)
    except ConnectionError:
        logger.critical('impersonator API is not running')
        raise
    if start:
        url = '{}/api/sync/sync/{}/{}/{}/none'.format(url_base, library.token.user.username, library.token.token, library.library_id) #FIXME: encryption not yet implemented
    else:
        url = '{}/api/sync/desync/{}/{}'.format(url_base, library.token.user.username, library.library_id)
    try:
        resp_info = requests.get(url, auth = A)
        rj = resp_info.json()
        if 'error' in rj:
            logger.warning('error to start={} synchronizing {} for user {} -- daemon response: {}'.format(start, library.library_id, library.token.user.username, rj))
            raise Exception(rj['error'])
        return rj['sync_folder'] if start else None
    except Exception as e:
        logger.error('error to start={} synchronizing {} for user {} -- {}'.format(start, library.library_id, library.token.user.username, e))

