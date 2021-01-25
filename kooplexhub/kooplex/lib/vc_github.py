
import github
import requests

def test_token(vctoken):
    client = github.Github(vctoken.token)
    try:
        client.get_user(vctoken.username)
    except github.GithubException as e:
        raise Exception(e.data['message'])

def list_projects(vctoken):
    client = github.Github(vctoken.token)
    for r in client.get_user().get_repos():
        yield {
                'id': r.id,
                'name': r.name,
                'description': r.description,
                'created_at': r.created_at,
                'updated_at': r.updated_at,
                'full_name': r.full_name,
                'owner_name': r.owner.login,
                'ssh_url': r.ssh_url
                }

def upload_rsa(vctoken):
    data = {
        "key": vctoken.rsa_pub,
        "title": "kooplex-hub"
    }
    headers = { 'Authorization': f'token {vctoken.token}' }
    R = requests.post(f'https://api.github.com/user/keys', json = data, headers = headers)
    assert R.status_code == 201, R.text
