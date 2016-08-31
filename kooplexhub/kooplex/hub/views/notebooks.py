﻿import os.path

from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect
from django.template import RequestContext
from datetime import datetime

from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session
from kooplex.lib.libbase import LibBase
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.lib.repo import Repo
from kooplex.lib.spawner import Spawner
from kooplex.lib.jupyter import Jupyter

ENTRY_NOTEBOOK_NAME = 'index.ipynb'
NOTEBOOK_DIR_NAME = 'notebooks'
HUB_NOTEBOOKS_URL = '/hub/notebooks'

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
    projects, unforkable_projectids = g.get_projects()

    gadmin = GitlabAdmin(request)
    public_projects = gadmin.get_all_public_projects(unforkable_projectids)

    return render(
        request,
        'app/notebooks.html',
        context_instance = RequestContext(request,
        {
            'notebooks': notebooks,
            'sessions': sessions,
            'projects': projects,
            'public_projects': public_projects,
            'username': username,
            'entry_notebook_name': ENTRY_NOTEBOOK_NAME,
            'notebook_dir_name': NOTEBOOK_DIR_NAME,
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
    notebook_path = LibBase.join_path(NOTEBOOK_DIR_NAME, notebook_name)
    jupyter.create_notebook(notebook_path)

    session = spawner.start_session(notebook_path, 'python3')
    url = session.external_url
    return HttpResponseRedirect(url)

def notebooks_shutdown(request):
    assert isinstance(request, HttpRequest)
    session_id = request.GET['session_id']
    session = Session.objects.filter(id=session_id)[0]
    username = request.user.username
    spawner = Spawner(username)
    spawner.stop_session(session)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def container_shutdown(request):
    assert isinstance(request, HttpRequest)
    notebook_id = request.GET['notebook_id']
    notebook = Notebook.objects.filter(id=notebook_id)[0]
    username = request.user.username
    spawner = Spawner(username)
    spawner.stop_notebook(notebook)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

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
    notebook_path = LibBase.join_path(notebook_path, ENTRY_NOTEBOOK_NAME)

    is_forked = eval(request.GET['is_forked'])
    if is_forked:
        project_id = int(request.GET['project_id'])
        target_id = int(request.GET['target_id'])
        session = spawner.start_session(notebook_path, 'python3', is_forked, project_id, target_id)
    else:
        session = spawner.start_session(notebook_path, 'python3')
    url = session.external_url
    return HttpResponseRedirect(url)

def notebooks_commit(request):
    assert isinstance(request, HttpRequest)
    notebook_path_dir = request.GET['notebook_path_dir']
    is_forked = request.GET['is_forked']
    project_id = 0
    target_id = 0
    if is_forked:
        project_id = request.GET['project_id']
        target_id = request.GET['target_id']
    return render(
        request,
        'app/commit.html',
        context_instance=RequestContext(request,
        {
            'notebook_path_dir': notebook_path_dir,
            'is_forked': is_forked,
            'project_id': project_id,
            'target_id': target_id,
        })
    )

def notebooks_commitform(request):
    assert isinstance(request, HttpRequest)
    notebook_path_dir = request.POST['notebook_path_dir']
    message = request.POST['message']
    is_forked = request.POST['is_forked']
    next_page = HUB_NOTEBOOKS_URL
    repo = Repo(request.user.username, notebook_path_dir)
    repo.commit_and_push(message, request.user.email)
    if is_forked:
        project_id = request.POST['project_id']
        target_id = request.POST['target_id']
        return render(
            request,
            'app/mergerequest.html',
            context_instance=RequestContext(request,
            {
                    'next_page': next_page,
                    'is_forked': is_forked,
                    'project_id': project_id,
                    'target_id': target_id,
            })
        )
    else:
        return HttpResponseRedirect(next_page)

def notebooks_mergerequestform(request):
    assert isinstance(request, HttpRequest)
    next_page = request.POST['next_page']
    project_id = request.POST['project_id']
    target_id = request.POST['target_id']
    title = request.POST['title']
    description = request.POST['description']
    g = Gitlab(request)
    message_json = g.create_mergerequest(project_id, target_id, title, description)
    if message_json == "":
        return HttpResponseRedirect(next_page)
    else:
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
            {
                    'error_title': 'Error',
                    'error_message': message_json,
            })
        )

def notebooks_mergerequestlist(request):
    assert isinstance(request, HttpRequest)
    itemid = request.GET['itemid']
    path_with_namespace = request.GET['path_with_namespace']
    g = Gitlab(request)
    mergerequests = g.list_mergerequests(itemid)
    return render(
        request,
        'app/mergerequestlist.html',
        context_instance=RequestContext(request,
        {
            'mergerequests': mergerequests,
            'path_with_namespace': path_with_namespace,
        })
    )

def notebooks_acceptmergerequest(request):
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    mergerequestid = request.GET['mergerequestid']
    g = Gitlab(request)
    message_json = g.accept_mergerequest(project_id, mergerequestid)
    if message_json == "":
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    else:
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
            {
                    'error_title': 'Error',
                    'error_message': message_json,
            })
        )

def project_fork(request):
    assert isinstance(request, HttpRequest)
    itemid = request.GET['itemid']
    g = Gitlab(request)
    message = g.fork_project(itemid)
    if message == "":
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    else:
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
            {
                    'error_title': 'Error',
                    'error_message': message,
            })
        )

urlpatterns = [
    url(r'^$', notebooks, name='notebooks'),
    url(r'^/new$', notebooks_new, name='notebooks-new'),
    url(r'^/shutdown$', notebooks_shutdown, name='notebooks-shutdown'),
    url(r'^/containershutdown$', container_shutdown, name='container-shutdown'),
    url(r'^/clone$', notebooks_clone, name = 'notebooks-clone'),
    url(r'^/commit$', notebooks_commit, name='notebooks-commit'),
    url(r'^/commitform$', notebooks_commitform, name='notebooks-commitform'),
    url(r'^/mergerequestform$', notebooks_mergerequestform, name='notebooks-mergerequestform'),
    url(r'^/mergerequestlist', notebooks_mergerequestlist, name='notebooks-mergerequestlist'),
    url(r'^/acceptmergerequest', notebooks_acceptmergerequest, name='notebooks-acceptmergerequest'),
    url(r'^/fork$', project_fork, name = 'project-fork'),
]