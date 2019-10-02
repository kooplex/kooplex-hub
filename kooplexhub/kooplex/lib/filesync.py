import seafileapi
import requests
import requests.auth

def list_libraries(fstoken):
    syncserver = fstoken.syncserver
    if syncserver.backend_type == syncserver.TP_SEAFILE:
        client = seafileapi.connect(syncserver.url, fstoken.user.username, fstoken.token, None)
        for r in client.repos.list_repos():
            yield r
    else:
        raise NotImplementedError("Unknown version control system type: %s" % fstoken.type)

def seafilepw_update(username, password):
    requests.get('http://kooplex-test-seafile-pw:5000/api/setpass/{}/{}'.format(username, password), auth = requests.auth.HTTPBasicAuth('hub', 'blabla'))

