import os
import logging
import hashlib
import MySQLdb
import seafileapi
import pickle
import base64
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
        raise NotImplementedError("Unknown filesyncronization service type: %s" % fstoken.backend_type)



def code_password_for_seafile(password):
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 10000)
    return "PBKDF2SHA256$10000$" + F(salt) +"$"+ F(key)

def store_user_pw(username, password):
    code = code_password_for_seafile(password)
    sqlq = "update EmailUser set passwd = '%s' where email = '%s';" % (code, username)
    dbhost = 'svc-seafile-mysql' #FIXME: hardcode os.getenv('MYSQL_HOST', 'seafile-mysql')
    pw = 'ALMAFA321' #FIXME: os.getenv('MYSQL_ROOT_PASSWORD')
    db = MySQLdb.connect(dbhost, "root", pw, "ccnet_db")
    c = db.cursor()
    c.execute(sqlq)
    c.close()
    db.commit()
    db.close()


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
    data_dict = {
            'service_url': library.token.syncserver.url, 
            'username': library.token.user.username,
            'password': library.token.token, 
            'libraryid': library.library_id, 
            'librarypassword': None,  #TODO
            }
    data = base64.b64encode(pickle.dumps(data_dict, protocol = 2))
    if start:
        url = f'{url_base}/api/sync/sync/{data}'
    else:
        url = '{url_base}/api/sync/desync/{data}'
    try:
        resp_info = requests.get(url, auth = A)
        rj = resp_info.json()
        if 'error' in rj:
            logger.warning(f'error to start={start} synchronizing {library.library_id} for user {library.token.user.username} -- daemon response: {rj}')
            raise Exception(rj['error'])
        return rj['sync_folder'] if start else None
    except Exception as e:
        logger.error(f'error to start={start} synchronizing {library.library_id} for user {library.token.user.username} -- daemon response: {rj}')

