
import gitlab

def list_projects(vctoken):
    client = gitlab.Gitlab(vctoken.repository.url, private_token = vctoken.token)
    for r in client.projects.list():
        yield r.path_with_namespace
