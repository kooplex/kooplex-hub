try:
    from kooplexhub.settings import KOOPLEX
except ImportError:
    KOOPLEX = {}

driver = KOOPLEX.get('driver', 'kubernetes')
if driver == 'kubernetes':
    from .kubernetes import start as start_environment, stop as stop_environment, check as check_environment, fetch_containerlog
    from .cluster_resources_api import Cluster
elif driver == 'docker':
    raise NotImplementedError
else:
    raise ImportError

