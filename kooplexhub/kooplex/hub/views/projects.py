from django.conf.urls import patterns, url, include
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.template import RequestContext

from kooplex.hub.models import *
from kooplex.lib import spawn_project_container


def projects(request, *v, **kw):
    """Renders the notebooks page"""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect(reverse('login'))

    PUBLIC = ScopeType.objects.get(name = 'public')
    user = User.objects.get(username = request.user.username)
    projects_mine = Project.objects.filter(owner = user)
    projects_sharedwithme = sorted([ upb.project for upb in UserProjectBinding.objects.filter(user = user) ])
    projects_public = sorted(Project.objects.filter(scope = PUBLIC).exclude(owner = user))
    images = Image.objects.all()
    scopes = ScopeType.objects.all()
    volumes = Volume.objects.all()
    volumes_attached = dict( map(lambda p: (p, [ vpb.volume for vpb in VolumeProjectBinding.objects.filter(project = p) ]), projects_mine) )
    #volumes_attached = dict( map(lambda p: (p, [ vpb.volume for vpb in VolumeProjectBinding.objects.filter(project = p) ]), projects_sharedwithme) )
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
            'images' : images,
            'scopes' : scopes,
            'volumes': volumes,
            'volumes_attached': volumes_attached,
            'errors' : kw.get('errors', None),
            'year' : 2018,
        })
    )

def project_new(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect(reverse('login'))
#FIXME:

def project_configure(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect(reverse('login'))
#FIXME:

def project_collaborate(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect(reverse('login'))
#FIXME:

def project_revision(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect(reverse('login'))
#FIXME:

def project_start(request):
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect(reverse('login'))

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
    spawn_project_container(request.user, project)   # TODO: check for error and get it back to user
    return redirect('projects')


urlpatterns = [
    url(r'^/?$', projects, name = 'projects'),
    url(r'^/new$', project_new, name = 'project-new'), 
    url(r'^/configure$', project_configure, name = 'project-settings'), 
    url(r'^/collaborate$', project_collaborate, name = 'project-members-form'), 
    url(r'^/revisioncontrol$', project_revision, name = 'project-commit'), 
    url(r'^/start$', project_start, name = 'container-start'), 
]

