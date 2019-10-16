
import gitlab

def list_projects(vctoken):
    client = gitlab.Gitlab(vctoken.repository.url, private_token = vctoken.token)
    for r in client.projects.list():
        yield {
                'id': r.id,
                'name': r.name,
                'description': r.description,
                'created_at': r.created_at,
                'updated_at': r.last_activity_at,
                'full_name': r.path_with_namespace,
                'owner_name': r.owner['username'],
                'ssh_url': r.ssh_url_to_repo
                }
