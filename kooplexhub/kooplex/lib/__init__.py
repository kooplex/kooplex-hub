"""
Package for the application.
"""

from .libbase import LibBase
from .restclient import RestClient

from .libbase import get_settings
#from .proxy import Proxy
from .docker import Docker
from .gitlab import  Gitlab
from .gitlabadmin import create_project as gitlab_create_project

from .filesystem import mkdir_homefolderstructure, write_davsecret, write_gitconfig, generate_rsakey, read_rsapubkey, mkdir_project, list_notebooks
from .filesystem import move_htmlreport_in_place, cleanup_reportfiles
from .impersonator import publish_htmlreport
from .sspawner import spawn_project_container, stop_project_container
from .jjupyter import proxy_addroute, proxy_removeroute
