import json
import logging

from kooplex.lib import get_settings
from kooplex.lib import Docker

logger = logging.getLogger(__name__)

class Spawner:

    def __init__(self, user, project, volumemapping):
        self.user = user.user
        self.project = project
#        self.containertype = containertype
        self.volumemapping = volumemapping
        container_name_info = { 'username': user.username, 'projectname': project.name_with_owner }
        self.container_name = get_settings('spawner', 'pattern_containername') % container_name_info
        self.docker = Docker()
#FIXME: 
#        logging.info("user %s, project: %s, containertype: %s" % (user, project, containertype))

    def get_container(self):
#FIXME: we may not need it, or may have DashboardContainer too here
        from kooplex.hub.models import ProjectContainer
        try:
            # the name of the container is unique
            return ProjectContainer.objects.get(name = self.container_name)
        except ProjectContainer.DoesNotExist:
            return None

    def new_container(self):
        from kooplex.hub.models import ProjectContainer
#FIXME:
        container = ProjectContainer(
            name = self.container_name,
            user = self.user,
            project = self.project,
        )
        # now we copy information from project to container instance
        container.save()
        container.init()
        return container

    def start_container(self, container):
        from kooplex.lib.proxy import addroute
        self.docker.run_container(container, self.volumemapping)
        container.is_running = True
        container.save()
        addroute(container)
        logger.info("container %s" % container)

    def run_container(self):
        container = self.get_container()
        if container is None:
            container = self.new_container()
        self.start_container(container)

#################################################################
#NOTE: these methods may belong to the project.py module

def spawn_project_container(user, project):
    from kooplex.lib.filesystem import G_OFFSET
    volumemapping = [
        (get_settings('spawner', 'volume-home'), '/mnt/.volumes/home', 'rw'),
        (get_settings('spawner', 'volume-git'), '/mnt/.volumes/git', 'rw'),
        (get_settings('spawner', 'volume-share'), '/mnt/.volumes/share', 'rw'),
    ]
    try:
        spawner = Spawner(user, project, volumemapping)
        spawner.run_container()
    except:
        raise

def stop_project_container(container):
    from kooplex.lib.proxy import removeroute
    logger.debug(container)
    try:
        removeroute(container)
    except KeyError:
        logger.warning("The proxy path was not existing: %s" % container)
        pass
    Docker().stop_container(container)

def remove_project_container(container):
    stop_project_container(container)
    logger.debug(container)
    Docker().remove_container(container)
    container.delete()

#################################################################
#NOTE: these methods may belong to the report.py module

## def spawn_report_container(report):
##     from kooplex.hub.models import ContainerType
## #    from kooplex.lib.filesystem import G_OFFSET
##     volumemapping = [
##         (get_settings('spawner', report-volume), '/home/', 'rw'),
##     ]
##     try:
##         dashboard = ContainerType.objects.get(name = 'dashboard')
##         spawner = Spawner(user, project, dashboard, volumemapping)
##         spawner.run_container()
##     except:
##         raise
## 
## def stop_project_container(container):
##     from kooplex.lib.proxy import removeroute
##     logger.debug(container)
##     try:
##         removeroute(container)
##     except KeyError:
##         logger.warning("The proxy path was not existing: %s" % container)
##         pass
##     Docker().stop_container(container)
## 
## def remove_project_container(container):
##     stop_project_container(container)
##     logger.debug(container)
##     Docker().remove_container(container)
##     container.delete()
