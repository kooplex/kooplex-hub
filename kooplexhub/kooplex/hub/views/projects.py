from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.template import RequestContext

from kooplex.hub.models import *
from kooplex.lib import spawn_project_container, stop_project_container


def projects(request, *v, **kw):
    """Renders the notebooks page"""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')

    PUBLIC = ScopeType.objects.get(name = 'public')
    NOTEBOOK = ContainerType.objects.get(name = 'notebook')
    user = request.user
    projects_mine = Project.objects.filter(owner = user)
    projects_sharedwithme = sorted([ upb.project for upb in UserProjectBinding.objects.filter(user = user) ])
    projects_public = sorted(Project.objects.filter(scope = PUBLIC).exclude(owner = user))
    running = [ c.project for c in Container.objects.filter(user = user, is_running = True, container_type = NOTEBOOK) ]
    images = Image.objects.all()
    scopes = ScopeType.objects.all()
    volumes = Volume.objects.all()
#FIXME:
#volumes

    return render(
        request,
        'project/projects.html',
        context_instance = RequestContext(request,
        {
            'user': user,
            'projects_mine': projects_mine,
            'projects_shared': projects_sharedwithme,
            'projects_public': projects_public,
            'running': running,
            'images' : images,
            'scopes' : scopes,
            'volumes': volumes,
            'errors' : kw.get('errors', None),
            'year' : 2018,
        })
    )

def project_new(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:

def project_configure(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:

def project_collaborate(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:

def project_revision(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:

def project_start(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')

    try:
        project_id = request.GET['project_id']
        project = Project.objects.get(id = project_id)
        if project.owner != request.user:
            UserProjectBinding(user = user, project = project)
    except KeyError:
        return redirect('/')
    except Project.DoesNotExist:
        return projects(request, kw = { 'errors': [ 'No such project' ] } )
    except UserProjectBinding.DoesNotExist:
        return projects(request, kw = { 'errors': [ 'You are not allowed to run this project. Ask %s for collaboration.' % project.owner ] } )
    spawn_project_container(request.user, project)
    return redirect('projects')

def project_open(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:

def project_stop(request):
    """Stop project and delete container."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
    
    user = request.user
    project_id = request.GET['project_id']
    try:
        project = Project.objects.get(id = project_id)
        container = Container.objects.get(user = user, project = project, is_running = True)
    except Project.DoesNotExist:
        return projects(request, kw = { 'errors': [ 'No such project' ] } )
    except Container.DoesNotExist:
        return projects(request, kw = { 'errors': [ 'Notebook container seems to be missing or not running already.' ] } )
    stop_project_container(container)
    return redirect('projects')

def project_publish(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:

urlpatterns = [
    url(r'^/?$', projects, name = 'projects'),
    url(r'^/new$', project_new, name = 'project-new'), 
    url(r'^/configure$', project_configure, name = 'project-settings'), 
    url(r'^/collaborate$', project_collaborate, name = 'project-members-form'), 
    url(r'^/revisioncontrol$', project_revision, name = 'project-commit'), 
    url(r'^/start$', project_start, name = 'container-start'), 
    url(r'^/open$', project_open, name = 'container-open'), 
    url(r'^/stop$', project_stop, name = 'container-delete'), 
    url(r'^/publish$', project_publish, name = 'notebooks-publishform'), 
]

