from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect
from django.template import RequestContext
from datetime import datetime

from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session
from kooplex.lib.libbase import LibBase
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.repo import Repo
from kooplex.lib.spawner import Spawner
from kooplex.lib.jupyter import Jupyter

def notebooks(request):
    """Renders the notebooks page"""
    assert isinstance(request, HttpRequest)

    username = request.user.username
    notebooks = Notebook.objects.filter(username=username)
    sessions = []
    for n in notebooks:
        ss = Session.objects.filter(notebook=n)
        for s in ss:
            sessions.append(s)
    g = Gitlab(request)
    projects = g.get_projects()
    
    return render(
        request,
        'app/notebooks.html',
        context_instance = RequestContext(request,
        {
            'notebooks': notebooks,
            'sessions': sessions,
            'projects': projects,
        })
    )

def notebooks_new(request):
    assert isinstance(request, HttpRequest)
    notebook_name = request.POST['notebook.name']
    notebook_name = notebook_name + '.ipynb'

    username = request.user.username
    spawner = Spawner(username)
    notebook = spawner.ensure_notebook_running()
    jupyter = Jupyter(notebook)

    ## TODO: remove hardcoding!
    notebook_path = LibBase.join_path('notebooks', notebook_name)
    jupyter.create_notebook(notebook_path)

    session = spawner.start_session(notebook_path, 'python3')
    url = session.external_url
    return HttpResponseRedirect(url)

def notebooks_shutdown(request):
    assert isinstance(request, HttpRequest)
    pass

def notebooks_clone(request):
    assert isinstance(request, HttpRequest)
    repo_name = request.GET['repo']
    repo = Repo(request.user.username, repo_name)
    repo.ensure_local_dir_empty()
    repo.clone()

    assert isinstance(request, HttpRequest)
    notebook_name = 'index'
    notebook_name = notebook_name + '.ipynb'

    username = request.user.username
    spawner = Spawner(username)
    notebook = spawner.ensure_notebook_running()
    jupyter = Jupyter(notebook)

    notebook_path = LibBase.join_path('projects/', repo_name)
    notebook_path = LibBase.join_path(notebook_path, 'index.ipynb')
    
    session = spawner.start_session(notebook_path, 'python3')
    url = session.external_url
    return HttpResponseRedirect(url)
    
    

urlpatterns = [
    url(r'^$', notebooks, name='notebooks'),
    url(r'^/new$', notebooks_new, name='notebooks-new'),
    url(r'^/shutdown$', notebooks_shutdown, name='notebooks-shutdown'),
    url(r'^/clone$', notebooks_clone, name = 'notebooks-clone'),
]