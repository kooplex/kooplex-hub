"""
@author: Jozsef Steger, David Visontai
@summary: project manipulation logic
"""
import logging

from kooplex.lib import Gitlab
from kooplex.hub.models import VolumeProjectBinding, UserProjectBinding

logger = logging.getLogger(__name__)

def create_project(project, volumes):
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
    logger.debug(project)
    for vpb in VolumeProjectBinding.objects.filter(project = project):
        logger.debug("removed volume project binding %s" % vpb)
        vpb.delete()
    for upb in UserProjectBinding.objects.filter(project = project):
        logger.debug("removed user project binding %s" % upb)
        upb.delete()
    g = Gitlab(project.owner)
    information = g.delete_project(project)
    logger.info("%s deleted" % project)
    project.delete()
