import logging
import seafileapi
import requests
import requests.auth

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
    #FIXME: url hardcoded
    requests.get('http://kooplex-test-seafile-pw:5000/api/setpass/{}/{}'.format(username, password), auth = requests.auth.HTTPBasicAuth('hub', 'blabla'))

def impersonator_sync(library, start):
    url_base = 'http://kooplex-test-impersonator:5000'
    A = requests.auth.HTTPBasicAuth('hub', 'blabla')
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

