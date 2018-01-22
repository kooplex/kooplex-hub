"""
@author: Jozsef Steger, David Visontai
@summary: project manipulation logic
"""
import logging

from kooplex.lib import Gitlab
from kooplex.hub.models import VolumeProjectBinding

logger = logging.getLogger(__name__)

def create_project(project, volumes):
    logger.debug("%s #volumes %d" % (project, len(volumes)))
    g = Gitlab(project.owner)
    information = g.create_project(project)
    project.save()
    for volume in volumes:
        vpb = VolumeProjectBinding(project = project, volume = volume)
        vpb.save()
        logger.debug(vpb)
    logger.info("%s created" % project)

