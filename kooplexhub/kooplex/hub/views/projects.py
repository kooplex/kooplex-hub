import re
import logging

from django.contrib import messages
from django.conf.urls import url, include
from django.shortcuts import render, redirect

from kooplex.hub.models import *
from kooplex.hub.views.extra_context import get_pane

from kooplex.logic.spawner import spawn_project_container, stop_container, SpawnError
from kooplex.logic import create_project, delete_project, configure_project, join_project, leave_project
from kooplex.logic import Repository, NotCheckedOut
from kooplex.lib.filesystem import create_clone_script
from kooplex.lib import authorize, get_settings

logger = logging.getLogger(__name__)

def projects(request):
    """Renders the projectlist page."""
    if not authorize(request):
        return redirect('login')
    try:
        PUBLIC = ScopeType.objects.get(name = 'public')
    except ScopeType.DoesNotExist:
        return redirect('/admin')
    user = request.user
    projects_mine = Project.objects.filter(owner = user)
    projects_sharedwithme = sorted([ upb.project for upb in UserProjectBinding.objects.filter(user = user) ])
    projects_public = sorted(Project.objects.filter(scope = PUBLIC).exclude(owner = user))
    running = [ c.project for c in ProjectContainer.objects.filter(user = user, is_running = True) ]
    stopped = [ c.project for c in ProjectContainer.objects.filter(user = user, is_running = False) ]
    users = sorted(User.objects.all())
    images = Image.objects.all()
    scopes = ScopeType.objects.all()
    functional_volumes = FunctionalVolume.objects.all()
    storage_volumes = list(user.volumes())
    logger.debug('Rendering projects.html')
    context_dict = {
        'user': user,
        'projects_mine': projects_mine,
        'projects_shared': projects_sharedwithme,
        'projects_public': projects_public,
        'running': running,
        'stopped': stopped,
        'users': users,
        'images' : images,
        'scopes' : scopes,
        'functional_volumes': functional_volumes,
        'storage_volumes': storage_volumes,
    }
    if hasattr(request, 'pane'):
        context_dict['pane'] = request.pane
    return render(
        request,
        'project/projects.html',
        context = context_dict
    )


def project_new(request):
    """Handles the creation of a new project."""
    if not authorize(request):
        return redirect('login')
    user = request.user
    name = request.POST['project_name'].strip()
    description = request.POST['project_description'].strip()
    button = request.POST['button']
    if button == 'Cancel':
        return redirect('projects')
    template = request.POST.get('project_template')
    volumes = [ FunctionalVolume.objects.get(name = x) for x in request.POST.getlist('func_volumes') ]
    for x in request.POST.getlist('stg_volumes'):
        v = StorageVolume.objects.get(name = x)
        if v in user.volumes():
            volumes.append(v)
    logger.debug('New project to be created: %s' % name)
    stop = False
    if not re.match(r'^[a-zA-Z][0-9a-zA-Z_\. -]*$', name):
        messages.error(request, 'For project name specification please use only Upper/lower case letters, hyphens, underscores, space and period.')
        stop = True
    if not re.match(r'^[0-9a-zA-Z_\. -]*$', description):
        messages.error(request, 'In your project description use only Upper/lower case letters, hyphens, spaces, underscores and period.')
        stop = True
    if stop:
        return redirect('projects')
        
    if template.startswith('clonable_project='):
        _, pidstr, _ = re.split(r'clonable_project=(\d+)', template)
        project_source = Project.objects.get(id = int(pidstr))
        image = project_source.image
        logger.debug('Project to be created from project: %s' % project_source)
        cloned_project = True
    elif template.startswith('image='):
        _, imagename, _ = re.split(r'image=(\w+)', template)
        image = Image.objects.get(name = imagename)
        logger.debug('Project to be created from image: %s' % imagename)
        cloned_project = False
    scope = ScopeType.objects.get(name = button)
    project = Project(name = name, owner = user, description = description, image = image, scope = scope)
    # NOTE: create_project takes good care of saving the new project instance
    try:
        create_project(project, volumes)
        if cloned_project:
            for volume in project_source.volumes:
                VolumeProjectBinding(project = project, volume = volume).save()
                logger.debug('volume %s bound to project %s' % (volume, project))
            create_clone_script(project, project_template = project_source)
        else:
            create_clone_script(project)
    except AssertionError:
        messages.error(request, 'Could not create project!. Wait for the administrator to respond!' )
        logger.error('Could not create project %s for user %s' % (name, user.username) )
        return redirect('projects')
    logger.debug('New project saved in HubDB: %s' % name)
    return redirect('projects')


def project_join(request):
    """Handles the joining of a public project."""
    if not authorize(request):
        return redirect('login')
    user = request.user
    try:
        PUBLIC = ScopeType.objects.get(name = 'public')
        project = Project.objects.get(id = request.GET.get('project_id', ''), scope = PUBLIC)
        if user in project.collaborators:
            logger.error('User %s cannot join the public project %s, as it is already a collaborator' % (user, project))
            messages.error(request, 'You are already a collaborator of the project %s owned by %s.' % (project.name, project.owner.username))
        else:
            join_project(project, user)
            logger.debug('User %s joins public project %s' % (user, project))
            messages.info(request, 'Joined public project %s owned by %s.' % (project.name, project.owner.username))
    except Project.DoesNotExist:
        logger.error('User %s cannot join public project %s, project may not be public, or not existing in hub' % (user, project))
        messages.error(request, 'You are not allowed to join the requested project.')
    except Exception as e:
        logger.error('User %s cannot join public project %s -- %s' % (user, project, e))
        messages.error(request, 'You cannot join the requested project. -- %s' % e)
    return redirect('projects')


def project_leave(request):
    """Handles the fact a collaborator wants to leave a public project."""
    if not authorize(request):
        return redirect('login')
    user = request.user
    try:
        PUBLIC = ScopeType.objects.get(name = 'public')
        project = Project.objects.get(id = request.GET.get('project_id', ''), scope = PUBLIC)
        if user in project.collaborators:
            leave_project(project, user)
            logger.debug('User %s leaves public project %s' % (user, project))
            messages.info(request, 'Left public project %s owned by %s.' % (project.name, project.owner.username))
        else:
            logger.error('User %s cannot leave public project %s, as it is not a collaborator' % (user, project))
            messages.error(request, 'You are not a collaborator of the project %s owned by %s.' % (project.name, project.owner.username))
    except Project.DoesNotExist:
        logger.error('User %s cannot leave public project %s, project may not be public, or not existing in hub' % (user, project))
        messages.error(request, 'You are not allowed to join the requested project.')
    except Exception as e:
        logger.error('User %s cannot leave public project %s -- %s' % (user, project, e))
        messages.error(request, 'You cannot join the requested project. -- %s' % e)
    return redirect('projects')


def project_configure(request):
    """Handles the project configuration."""
    if not authorize(request):
        return redirect('login')
    if request.method != 'POST':
        return redirect('projects')
    button = request.POST['button']
    project_id = request.POST['project_id']
    try:
        project = Project.objects.get(id = project_id)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect('projects')
    if button == 'delete':
        if project.owner == request.user:
            delete_project(project)
        else:
            messages.error(request, 'Project %s is not yours' % project)
            return redirect('projects')
    elif button == 'quit':
        if project.owner == request.user:
            messages.error(request, 'You are the owner of the project %s, you cannot leave it' % project)
            return redirect('projects')
        else:
            leave_project(project, request.user)
    elif button == 'apply':
        if project.owner != request.user:
            messages.warning(request, 'Currently only project owners can modify project')
            return redirect('projects')
        collaborators = [ User.objects.get(id = x) for x in request.POST.getlist('collaborators') ]
        volumes = [ FunctionalVolume.objects.get(name = x) for x in request.POST.getlist('func_volumes') ]
        volumes.extend( [ StorageVolume.objects.get(name = x) for x in request.POST.getlist('stg_volumes') ] )
        image = Image.objects.get(name = request.POST['project_image'])
        scope = ScopeType.objects.get(name = request.POST['project_scope'])
        marked_to_remove = configure_project(project, image, scope, volumes, collaborators)
        if marked_to_remove:
            messages.info(request, 'Running container of project %s is going to be removed when you stop. Mount point changes take effect after restarting them.' % project)
    return redirect('projects')


def project_start(request):
    """Starts. the project container."""
    if not authorize(request):
        return redirect('login')
    request.pane = get_pane(request)
    try:
        project_id = request.GET['project_id']
        project = Project.objects.get(id = project_id)
        if project.owner != request.user:
            UserProjectBinding(user = request.user, project = project)
        spawn_project_container(request.user, project)
    except KeyError:
        return redirect('/')
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
    except UserProjectBinding.DoesNotExist:
        messages.error(request, 'You are not authorized to start that project')
    except SpawnError as e:
        messages.error(request, 'We cannot start the container -- %s' % e)
    return projects(request)

def project_open(request):
    """Opens the project container."""
    if not authorize(request):
        return redirect('login')
    user = request.user
    project_id = request.GET.get('project_id', None)
    try:
        project = Project.objects.get(id = project_id)
        container = ProjectContainer.objects.get(user = user, project = project, is_running = True)
        container.wait_until_ready()
        return redirect(container.url_external)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
    except ProjectContainer.DoesNotExist:
        messages.error(request, 'Project container is missing or stopped')
    #except ConnectionError:
    #    messages.error(request, 'Could not open it. Try again, please! If you keep seeing this error then ask an administrator <strong> %s </strong>'%get_settings('hub', 'adminemail'))
    return redirect('projects')


def project_stop(request):
    """Stops project and delete container."""
    if not authorize(request):
        return redirect('login')
    user = request.user
    project_id = request.GET.get('project_id', None)
    request.pane = get_pane(request)
    try:
        project = Project.objects.get(id = project_id)
        container = ProjectContainer.objects.get(user = user, project = project, is_running = True)
        stop_container(container)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
    except ProjectContainer.DoesNotExist:
        messages.error(request, 'Project container is already stopped or is missing')
    return projects(request)

def project_versioning(request):
    """Handles the git."""
    if not authorize(request):
        return redirect('login')
    if request.method != 'GET':
        return redirect('projects')
    user = request.user
    try:
        project = Project.objects.get(id = request.GET.get('project_id', -1))
        if project.owner != user and not user in project.collaborators:
            messages.error(request, 'You are not allowed to version control this project.')
            return redirect('projects')
        try:
            repo = Repository(user, project)
        except NotCheckedOut:
            messages.error(request, 'You are not allowed to version control this project until you first start the project container.')
            return redirect('projects')
        git_log = repo.log()
        git_files = repo.lsfiles()
        git_changed = repo.remote_changed()
        logger.debug('Rendering gitform.html')
        return render(
            request,
            'project/gitform.html',
            context =
            {
                'project': project,
                'committable_dict' : git_files,
                'commits' : git_log,
                'changedremote': git_changed,
            }
        )
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect('projects')
    except ValueError:
        messages.error(request, 'Something went wrong! Please try to start first your project. If you keep seeing this error then ask an administrator %s '%get_settings('hub', 'adminemail'))
        return redirect('projects')


def project_versioning_commit(request):
    """Handles the git."""
    if not authorize(request):
        return redirect('login')
    if request.method != 'POST':
        return redirect('projects')
    if request.POST['button'] == 'Cancel':
        return redirect('projects')
    user = request.user
    try:
        project = Project.objects.get(id = request.POST['project_id'])
        if project.owner != user and not user in project.collaborators:
            messages.error(request, 'You are not allowed to version control this project')
            return redirect('projects')
        message = request.POST['message']
        repo = Repository(request.user, project)
        repo.add( request.POST.getlist('modified_files') )
        repo.add( request.POST.getlist('other_files') )
        repo.remove( request.POST.getlist('deleted_files') )
        repo.commit(message)
        repo.push()
        return redirect('projects')
    except Exception as e:
        msg = "Unhandled exception -- %s" % e
        messages.error(request, msg)
        logger.error(msg)
    return redirect('projects')


def project_versioning_revert(request):
    """Handles the git."""
    if not authorize(request):
        return redirect('login')
    if request.method != 'POST':
        return redirect('projects')
    if request.POST['button'] == 'Cancel':
        return redirect('projects')
    user = request.user
    try:
        project = Project.objects.get(id = request.POST['project_id'])
        if project.owner != user and not user in project.collaborators:
            messages.error(request, 'You are not allowed to version control this project')
            return redirect('projects')
        commitid = request.POST['commitid']
        repo = Repository(request.user, project)
        repo.revert(commitid)
        return redirect('projects')
    except Exception as e:
        msg = "Unhandled exception -- %s" % e
        messages.error(request, msg)
        logger.error(msg)
    return redirect('projects')


def project_versioning_pull(request):
    """Handles the git."""
    if not authorize(request):
        return redirect('login')
    if request.method != 'POST':
        return redirect('projects')
    if request.POST['button'] == 'Cancel':
        return redirect('projects')
    user = request.user
    try:
        project = Project.objects.get(id = request.POST['project_id'])
        if project.owner != user and not user in project.collaborators:
            messages.error(request, 'You are not allowed to version control this project')
            return redirect('projects')
        repo = Repository(request.user, project)
        repo.pull()
        return redirect('projects')
    except Exception as e:
        msg = "Unhandled exception -- %s" % e
        messages.error(request, msg)
        logger.error(msg)
    return redirect('projects')



urlpatterns = [
    url(r'^/?$', projects, name = 'projects'),
    url(r'^/new$', project_new, name = 'project-new'), 
    url(r'^/join$', project_join, name = 'project-join'), 
    url(r'^/leave$', project_leave, name = 'project-leave'), 
    url(r'^/configure$', project_configure, name = 'project-settings'), 
    url(r'^/versioncontrol$', project_versioning, name = 'project-versioncontrol'), 
    url(r'^/versioncontrol/commit$', project_versioning_commit, name = 'project-commit'), 
    url(r'^/versioncontrol/revert$', project_versioning_revert, name = 'project-revert'), 
    url(r'^/versioncontrol/pull$', project_versioning_pull, name = 'project-pull'), 
    url(r'^/start$', project_start, name = 'container-start'), 
    url(r'^/open$', project_open, name = 'container-open'), 
    url(r'^/stop$', project_stop, name = 'container-delete'), 
]

