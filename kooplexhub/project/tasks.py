import logging
import time

from django.db.models import Count
from channels.layers import get_channel_layer
from django_huey import db_task, task, periodic_task
from huey import crontab
from asgiref.sync import async_to_sync

from django.contrib.auth.models import User
from django.db import transaction

from hub.models import Group
from hub.lib import archivedir, extracttarbal
from hub.lib import grantaccess_user, revokeaccess_user
from hub.lib import grantaccess_group, revokeaccess_group
from hub.lib import mkdir, archivedir, rmdir
from hub.lib.ldap import Ldap
from kooplexhub.lib import bash
from .models import Project
from project import fs

logger = logging.getLogger(__name__)

@periodic_task(crontab(minute="*/15"), queue='project')
def sync_project_groups():
    # ldap project groups
    l=Ldap()
    g_ldap = list(filter(lambda x: x.startswith('p-'), l.groups()))
    # make projects that have collaborators have groups related
    qs = (
        Project.objects
        .annotate(num_bindings=Count('userbindings'))
        .filter(num_bindings__gt=1)
    )
    for p in qs:
        logger.debug(f'Test groups for project {p}')
        gn=p.groupname
        if g:=p.group:
            if gn in g_ldap:
                g_ldap.remove(gn)
                logger.debug(f'Project {p} has group and ldap group: {gn}')
            else:
                logger.error(f'Project {p} has group, but ldap entry is missing')
                l.addgroup(g)
                #FIXME add userbindings also
        else:
            logger.error(f'Project {p} is missing group')
            Group.objects.create(name=gn, grouptype=Group.TP_PROJECT)
            if gn in g_ldap:
                logger.warning(f'ldap entry {gn} was present anyway')
                g_ldap.remove(gn)
    # remove unused ldap entries
    for lg in g_ldap:
        logger.info(f'Removing unused ldap entry {lg}')
        try:
            l.removegroup(Group(name=lg))
        except Exception as e:
            logger.critical(e)
    return "Completed"


@task(queue = 'project')
def grant_access(project, group_created):
    for folder in [ fs.path_project(project), fs.path_report_prepare(project) ]:
        logger.debug(f"project folder {folder} group? {group_created} (creator: {project.creator}, group: {project.group})")
        if group_created:
            grantaccess_group(project.group, folder, readonly = False, recursive = True)
        else:
            grantaccess_user(project.creator, folder, readonly = False, recursive = True)
#    channel_layer=get_channel_layer()
#    async_to_sync(channel_layer.group_send)("project", {
#            "type": "feedback",
#            "feedback": f"Folders {folders} got acl {acl}",
#        })
    return "Completed"





