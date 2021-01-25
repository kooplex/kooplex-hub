
import requests

def test_token(vctoken):
    R = requests.get(f'{vctoken.repository.url}/api/v1/version', params = { 'token': vctoken.token })
    assert R.status_code == 200, R.text


def list_projects(vctoken):
    R = requests.get(f'{vctoken.repository.url}/api/v1/users/{vctoken.username}/repos', params = { 'token': vctoken.token })
    assert R.status_code == 200, R.text
    for r in R.json():
        yield {
                'id': r['id'],
                'name': r['name'],
                'description': r['description'],
                'created_at': r['created_at'],
                'updated_at': r['updated_at'],
                'full_name': r['full_name'],
                'owner_name': r['owner']['login'],
                'ssh_url': r['ssh_url']
                }

def upload_rsa(vctoken):
    data = {
        "key": vctoken.rsa_pub,
        "read_only": True,
        "title": "kooplex-hub"
    }
    R = requests.post(f'{vctoken.repository.url}/api/v1/user/keys', json = data, params = { 'token': vctoken.token })
    assert R.status_code == 201, R.text

#def create_user(user):
#    client = pytea.API(vctoken.repository.url, token = vctoken.token)
#    {
#  "email": "user@example.com",
#  "full_name": "string",
#  "login_name": "string",
#  "must_change_password": true,
#  "password": "string",
#  "send_notify": true,
#  "source_id": 0,
#  "username": "string"
#}

