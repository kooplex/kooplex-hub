
import github

def list_projects(vctoken):
    client = github.Github(vctoken.token)
    for r in client.get_user().get_repos():
        yield r.full_name
