import json
import logging
from threading import Timer

from kooplex.lib import get_settings
from kooplex.lib import Docker
from kooplex.hub.models import ProjectContainer, DashboardContainer

logger = logging.getLogger(__name__)

class Spawner:

    def __init__(self, container):
        self.docker = Docker()
        if isinstance(container, ProjectContainer):
            try:
                container_from_model = ProjectContainer.objects.get(user = container.user, project = container.project)
                logger.debug('ProjectContainer present in hubdb: %s' % container_from_model)
                present = True
            except ProjectContainer.DoesNotExist:
                logger.debug('ProjectContainer not present in hubdb')
                present = False
        elif isinstance(container, DashboardContainer):
        #FIXME: new for each Anonym request...
        #    try:
        #        #FIXME: Anonymous
        #        #container_from_model = DashboardContainer.objects.get(user = container.user, report = container.report)
        #        container_from_model = DashboardContainer.objects.get(report = container.report)
        #        logger.debug('DashboardContainer present in hubdb: %s' % container_from_model)
        #        present = True
        #    except DashboardContainer.DoesNotExist:
        #        logger.debug('DashboardContainer not present in hubdb')
                present = False
        if present:
            self.container = container_from_model
        else:
            container.save()
            container.init()
            self.container = container
        logging.debug("spawner for container %s" % self.container)

    def run_container(self): #NOTE: shall we check docker API?
        if self.container.is_running:
            logging.debug("container %s is running" % self.container)
        else:
            self.start_container()
            logging.debug("container %s is running" % self.container)

    def start_container(self):
        from kooplex.lib.proxy import addroute
        self.docker.run_container(self.container)
        self.container.is_running = True
        self.container.save()
        addroute(self.container)
        logger.info("started %s" % self.container)


#################################################################

class SpawnError(Exception):
    pass

def spawn_project_container(user, project):
    from docker import errors
    container = ProjectContainer(
        user = user,
        project = project,
    )
    try:
        spawner = Spawner(container)
        spawner.run_container()
        logger.debug('spawner new container: %s' % container)
    except errors.NotFound as e:
        logger.error('container: %s -- %s' % (container, e))
        remove_container(container)
        raise SpawnError(e.explanation)
    except:
        raise

def register_check_timer(container, first_time = True):
    logger.debug("register checker %s" % container)
    dt = get_settings('spawner', 'checkpasswordinterval_dashboard') if first_time else get_settings('spawner', 'checkinterval_dashboard')
    Timer(dt, check_dashboard, (container, )).start()


def check_dashboard(container, n):
    from kooplex.lib import jupyter_session
    response = jupyter_session(container).json()
    logger.debug("%s -- %s" % (container, response))
    starting_kernel = False
    if len(response):
        connections = 0
        for r in response:
            connections += r['kernel']['connections']
            starting_kernel |= r['kernel']['execution_state'] == 'starting'
        logger.debug("%d kernels in %s" % (connections, container))
    else:
        logger.info("no password provided in time %s" % container)
        stop_container(container)
    if (connections == 0) and not starting_kernel:
        logger.info("no more kernels, stopping container %s" % container)
        stop_container(container)
    else:
        register_check_timer(container, first_time = False)
        

def spawn_dashboard_container(report):
    container = DashboardContainer(
#FIXME: user is not used unauthenticated launch
#        user = user,
        report = report,
    )
    try:
        spawner = Spawner(container)
        spawner.run_container()
        container.wait_until_ready()
        register_check_timer(container)
        return container.url_external
    except:
        raise

def stop_container(container):
    from kooplex.lib.proxy import removeroute
    logger.debug(container)
    try:
        removeroute(container)
    except KeyError:
        logger.warning("The proxy path was not existing: %s" % container)
        pass
    Docker().stop_container(container)

def remove_container(container):
    stop_container(container)
    logger.debug(container)
    Docker().remove_container(container)
