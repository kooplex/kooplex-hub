
from .vc_github import list_projects as lp_gh
from .vc_gitlab import list_projects as lp_gl

def list_projects(vctoken):
    repository = vctoken.repository
    if repository.backend_type == repository.TP_GITHUB:
        return lp_gh(vctoken)
    elif repository.backend_type == repository.TP_GITLAB:
        return lp_gl(vctoken)
    else:
        raise NotImplementedError("Unknown version control system type: %s" % vctoken.type)
