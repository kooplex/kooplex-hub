
from .vc_github import list_projects as lp_gh
from .vc_gitlab import list_projects as lp_gl

def list_projects(vctoken):
    if vctoken.backend_type == vctoken.TP_GITHUB:
        return lp_gh(vctoken)
    elif vctoken.backend_type == vctoken.TP_GITLAB:
        return lp_gl(vctoken)
    else:
        raise NotImplementedError("Unknown version control system type: %s" % vctoken.type)
