
import pytea
import logging
logger = logging.getLogger(__name__)

def list_projects(vctoken):
    client = pytea.API(vctoken.repository.url, token = vctoken.token)
    R = client.get('/users/{}/repos'.format(vctoken.username))
    assert R.status_code == 200, R.reason
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

