#FIXME: should be registered to signal pre_save
"""
@author: Jozsef Steger, David Visontai
@summary: project manipulation logic
"""
import logging

from kooplex.lib import Docker

logger = logging.getLogger(__name__)


def configure_project(project, **kw):#image, scope, volumes, collaborators, description):
    from hub.models import VolumeProjectBinding
    """
    @summary: configure a user project
              1. set image and scope
              2. manage volume project bindings
              3. manage user project bindings and manage gitlab sharing
    @param project: the project model
    @type project: kooplex.hub.models.Project
    @param kw: the values to set
    @type kw: dict of parameters to set
    @return the number of running containers marked to be removed
    """
    mark_to_remove = False
    logger.debug(project)
    volumes = set(kw.get('volumes', []))
    

    old_volumes = set(project.functional_volumes).union(project.storage_volumes)    

    logger.debug("old: %s new: %s" % (old_volumes, volumes))

    if old_volumes != volumes:
        mark_to_remove = True
        vol_remove = old_volumes.difference( volumes )
        vol_add = volumes.difference( old_volumes )
        logger.debug("- %s" % vol_remove)
        for volume in vol_remove:
            VolumeProjectBinding.objects.get(volume = volume, project = project).delete()
        logger.debug("+ %s" % vol_add)
        for volume in vol_add:
            VolumeProjectBinding.objects.create(volume = volume, project = project)
    

#    project.scope = scope
#    for vpb in VolumeProjectBinding.objects.filter(project = project):
#        if vpb.childvolume in volumes:
#            logger.debug("volume project binding remains %s" % vpb)
#            volumes.remove(vpb.childvolume)
#        else:
#            mark_to_remove = True
#            logger.debug("volume project binding removed %s" % vpb)
#            vpb.delete()
#    for volume in volumes:
#        mark_to_remove = True
#        vpb = VolumeProjectBinding(project = project, volume = volume)
#        logger.debug("volume project binding added %s" % vpb)
#        vpb.save()
#    for upb in UserProjectBinding.objects.filter(project = project):
#        if upb.user in collaborators:
#            logger.debug("collaborator remains %s" % upb)
#            collaborators.remove(upb.user)
#        else:
#            logger.debug("collaborator removed %s" % upb)
#            unshare_project_oc(project, upb.user)
#            upb.delete()
#    for user in collaborators:
#        join_project(project, user, gitlab)
    n_affected_running_containers = mark_containers_remove(project) if mark_to_remove else 0
    project.save()
    return n_affected_running_containers

def mark_containers_remove(project):
    """
    @summary: mark project containers to be removed when they are stopped next time. In case the container is already stopped, remove them
    @param project: the project model
    @type project: kooplex.hub.models.Project
    @returns the number of containers marked for removal
    @rtype int
    """
    n_mark = 0
    n_remove = 0
    for container in project.containers:
        if container.is_running:
            container.mark_to_remove = True
            container.save()
            n_mark += 1
        else:
            Docker().remove_container(container)
            n_remove += 1
    logger.info("project %s: %d containers removed, %d containers marked for removal" % (project, n_remove, n_mark))
    return n_mark

#def join_project(project, user, gitlab = None):
#    """
#    @summary: join a user project
#              1. add a new user project binding
#              2. owncloud share
#              3. gitlab project on the user's behalf
#    @param project: the project model
#    @type project: kooplex.hub.models.Project
#    @param user: the collaborator to join the project
#    @type user: kooplex.hub.models.User
#    @param gitlab: a gitlab driver instance, defaults to None, which means we are initializing a new here
#    @type gitlab: kooplex.lib.Gitlab
#    """
#    if gitlab is None:
#        gitlab = Gitlab(project.owner)
#    logger.debug(project)
#    upb = UserProjectBinding(project = project, user = user)
#    logger.debug("collaborator added %s" % upb)
#    share_project_oc(project, upb.user)
#    gitlab.add_project_member(project, upb.user)
#    mkdir_git_workdir(upb.user, project)
#    create_clone_script(project, collaboratoruser = upb.user)
#    upb.save()
#    logger.info("%s joins project %s" % (user, project))

#def leave_project(project, user):
#    """
#    @summary: leave a user project
#              1. remove user project binding
#              2. garbage collect data in git workdir
#              3. owncloud unshare
#              6. get rid of containers if any
#              7. delete gitlab project on the user's behalf
#    @param project: the project model
#    @type project: kooplex.hub.models.Project
#    @param user: the collaborator to leave the project
#    @type user: kooplex.hub.models.User
#    """
#    logger.debug(project)
#    try:
#        upb = UserProjectBinding.objects.get(project = project, user = user)
#        upb.delete()
#        logger.debug('user project binding removed: %s' % upb)
#    except UserProjectBinding.DoesNotExist:
#        msg = 'user %s is not bound to project %s' % (user, project)
#        logger.error(msg)
#        return msg
#    gitlab = Gitlab(project.owner)
#    cleanup_git_workdir(user, project)
#    unshare_project_oc(project, user)
#    gitlab.delete_project_member(project, user)
#    try:
#        container = ProjectContainer.objects.get(user = user, project = project)
#        logger.debug("remove container %s" % container)
#        remove_container(container)
#    except ProjectContainer.DoesNotExist:
#        logger.debug("%s has no container" % project)
#    logger.info("%s left project %s" % (user, project))

