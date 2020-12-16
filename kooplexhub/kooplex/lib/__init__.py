from .libbase import standardize_str, deaccent_str, keeptrying, bash, now, translate_date, human_localtime, custom_redirect, sudo
from .docker import Docker
from .versioncontrol import list_projects, impersonator_repo
from .filesync import list_libraries, seafilepw_update, impersonator_sync
from .fs_filename import Filename
from .fs_dirname import Dirname
from .call_api import add_report_nginx_api, remove_report_nginx_api

from kooplex.settings import KOOPLEX

driver = KOOPLEX.get('spawner').get('driver')
if driver == 'kubernetes':
    from .kubernetes import start as start_environment, stop as stop_environment, check as check_environment
elif driver == 'docker':
    raise NotImplementedError
else:
    raise ImportError

