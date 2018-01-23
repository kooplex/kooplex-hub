'''
@author: Jozsef Steger
@summary: in favour of a user run commands or scripts in a container
'''
import logging

from kooplex.lib import get_settings, Docker
from kooplex.lib.filesystem import move_htmlreport_in_place
from kooplex.hub.models import Container

logger = logging.getLogger(__name__)

def publish_htmlreport(report):
    from kooplex.hub.models import Container
    logger.debug(report)
    # select the user's project container, which should be running
    container = Container.objects.get(user = report.creator, project = report.project, is_running = True)
    # run conversion behalf of the user
    command = 'jupyter-nbconvert --to html %s' % report.filename
    response = Docker().execute(container, command)
    # mv result files in place
    move_htmlreport_in_place(report)

def get_impersonator_container():
    #NOTE: do not save this container instance. It is just used to interface with the docker API
    return Container(name = get_settings('impersonator', 'container_name'))

def mkdir_project_oc(project):
    logger.debug(project)
    directory = '_project.' + project.name_with_owner
    command = 'sudo -i -u %s sh -c "share.sh mkdir %s"' % (project.owner.username, directory)
    Docker().execute(get_impersonator_container(), command)

def share_project_oc(project, user):
    logger.debug(project)
    directory = '_project.' + project.name_with_owner
    command = 'sudo -i -u %s sh -c "share.sh share %s %s"' % (project.owner.username, directory, user.username)
    Docker().execute(get_impersonator_container(), command)

def share_project_oc(project, user):
    logger.debug(project)
    directory = '_project.' + project.name_with_owner
    command = 'sudo -i -u %s sh -c "share.sh unshare %s %s"' % (project.owner.username, directory, user.username)
    Docker().execute(get_impersonator_container(), command)

