
import pytea

def list_projects(vctoken):
    client = pytea.API(vctoken.repository.url, token = vctoken.token)
    R = client.get('/users/{}/repos'.format(vctoken.user.username))
    for r in R.json():
        yield r['full_name']
