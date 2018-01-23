"""
@author: Jozsef Steger, David Visontai
@summary: project manipulation logic
"""
import logging

from kooplex.lib import Gitlab
from kooplex.hub.models import VolumeProjectBinding, UserProjectBinding, Container
from .spawner import remove_project_container

logger = logging.getLogger(__name__)

def create_project(project, volumes):
#FIXME: 3, 4, 5 not implemnted
    """
    @summary: create a new user project
              1. create gitlab project behalf of the user
              2. save project volume bindings
              3. create share
              4. create owncloud workdir
              5. create git workdir
    @param project: the project model
    @type project: kooplex.hub.models.Project
    @param volumes: volumes to bind with the project
    @type volumes: list of kooplex.hub.models.Volume
    """
    logger.debug("%s #volumes %d" % (project, len(volumes)))
    g = Gitlab(project.owner)
    information = g.create_project(project)
    project.save()
    for volume in volumes:
        vpb = VolumeProjectBinding(project = project, volume = volume)
        vpb.save()
        logger.debug("new volume project binding %s" % vpb)
    logger.info("%s created" % project)

def delete_project(project):
#FIXME: 2, 3, 4 not implemnted
    """
    @summary: delete a user project
              1. remove project volume bindings
              2. garbage collect data in share
              3. garbage collect data in git workdir
              4. owncloud unshare
              5. remove user project binding
              6. get rid of containers if any
              7. delete gitlab project on the user's behalf
    @param project: the project model
    @type project: kooplex.hub.models.Project
    """
    logger.debug(project)
    for vpb in VolumeProjectBinding.objects.filter(project = project):
        logger.debug("removed volume project binding %s" % vpb)
        vpb.delete()
#FIXME
    for upb in UserProjectBinding.objects.filter(project = project):
        logger.debug("removed user project binding %s" % upb)
        upb.delete()
    try:
        container = Container.objects.get(user = project.owner, project = project)
        logger.debug("remove container %s" % container)
        remove_project_container(container)
    except Container.DoesNotExist:
        logger.debug("%s has no container" % project)
    g = Gitlab(project.owner)
    information = g.delete_project(project)
    logger.info("%s deleted" % project)
    project.delete()

def configure_project(project, image, scope, volumes, collaborators):
    logger.debug(project)
    project.image = image
    project.scop = scope
    for vpb in VolumeProjectBinding.objects.filter(project = project):
        if vpb.childvolume in volumes:
            logger.debug("volume project binding remains %s" % vpb)
            volumes.remove(vpb.childvolume)
        else:
            logger.debug("volume project binding removed %s" % vpb)
            vpb.delete()
    for volume in volumes:
        vpb = VolumeProjectBinding(project = project, volume = volume)
        logger.debug("volume project binding added %s" % vpb)
        vpb.save()
    for upb in UserProjectBinding.objects.filter(project = project):
        if upb.user in collaborators:
            logger.debug("collaborator remains %s" % upb)
            collaborators.remove(upb.user)
        else:
            logger.debug("collaborator removed %s" % upb)
            upb.delete()
    for user in collaborators:
        upb = UserProjectBinding(project = project, user = user)
        logger.debug("collaborator added %s" % upb)
        upb.save()
    project.save()

