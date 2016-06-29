from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect
from django.template import RequestContext
from datetime import datetime

from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session
from kooplex.lib.libbase import LibBase
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.spawner import Spawner
from kooplex.lib.jupyter import Jupyter

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
    notebook_name = request.POST['notebook.name']
    notebook_name = notebook_name + '.ipynb'
    ## TODO: remove hardcoding!
    notebook_path = LibBase.join_path('notebooks', notebook_name)
    spawner = Spawner(username)
    notebook = spawner.ensure_notebook_running()
    jupyter = Jupyter(notebook)
    jupyter.create_notebook(notebook_path)
    session = spawner.start_session(notebook_path, 'python3')
    url = session.external_url
    return HttpResponseRedirect(url)

def notebooks_spawn(request):
    assert isinstance(request, HttpRequest)
    return None

urlpatterns = [
    url(r'^$', notebooks, name='notebooks'),
    url(r'^/new$', notebooks_new, name='notebooks-new'),
]