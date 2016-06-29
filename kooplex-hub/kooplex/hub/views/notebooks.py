from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect
from django.template import RequestContext
from datetime import datetime

from kooplex.hub.models.notebook import Notebook
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner

def notebooks(request):
    """Renders the notebooks page"""
    assert isinstance(request, HttpRequest)

    username = request.user.username
    notebooks = Notebook.objects.filter(username=username)
    g = Gitlab(request)
    projects = g.get_projects()
    
    return render(
        request,
        'app/notebooks.html',
        context_instance = RequestContext(request,
        {
            'notebooks': notebooks,
            'projects': projects,
        })
    )

def notebooks_new(request):
    assert isinstance(request, HttpRequest)

    username = request.user.username
    spawner = Spawner(username)
    notebook = spawner.ensure_notebook_running()
    url = notebook.external_url
    return HttpResponseRedirect(url)

def notebooks_spawn(request):
    assert isinstance(request, HttpRequest)
    return None

urlpatterns = [
    url(r'^$', notebooks, name='notebooks'),
    url(r'^/new$', notebooks_new, name='notebooks-new'),
]