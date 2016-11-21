import os.path

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
from kooplex.lib.smartdocker import Docker
import git

NOTEBOOK_DIR_NAME = 'notebooks'
HUB_NOTEBOOKS_URL = '/hub/notebooks'

def notebooks(request):
    """Renders the notebooks page"""
    assert isinstance(request, HttpRequest)

    username = request.user.username
    print("debug=1")
    notebooks = Notebook.objects.filter(username=username)
    sessions = []
    for n in notebooks:
        ss = Session.objects.filter(notebook=n)
        for s in ss:
            sessions.append(s)
    print("debug=2")
    g = Gitlab(request)
    projects, unforkable_projectids = g.get_projects()
    print("debug=3")
    for project in projects:
        variables=g.get_project_variables(project['id'])
        project['variables']=variables
    print("debug=4")
    print("If something is odd, may you forgot to init hub, otherwise no error comes here :|")
    #TODO: get uid and gid from projects json
    gadmin = GitlabAdmin(request)
    public_projects = gadmin.get_all_public_projects(unforkable_projectids)
    print("debug=5")
    d = Docker()
    notebook_images = d.get_allnotebook_images()
    print("debug=6")
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
            'notebook_dir_name': NOTEBOOK_DIR_NAME,
            'notebook_images' : notebook_images,
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

    session = spawner.start_session(notebook_path, 'python3', container_name)
    url = session.external_url
    return HttpResponseRedirect(url)
    
def project_new(request):
    assert isinstance(request, HttpRequest)
    project_name = request.POST['project.name']
    project_image_name = request.POST['project.image']
    public = request.POST['project.public']
    description = request.POST['project.public']
    g = Gitlab(request)

    message_json = g.create_project(project_name,public,description)
    res = g.get_project_by_name(project_name)
    if len(res)>1:
        "Error to the log: there more than 1 project which is not acceptable!!!!"
    else:
        project_id=res[0]['id']
    print(project_image_name)

    #add image_name to project
    g.create_project_variable(project_id,'container_image', project_image_name)

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

def notebooks_shutdown(request):
    assert isinstance(request, HttpRequest)
    session_id = request.GET['session_id']
    print(session_id)
    session = Session.objects.filter(id=session_id)[0]

    username = request.user.username
    repo_name = session.repo_name

    #repo_name = ""
    spawner = Spawner(username,repo_name)
    spawner.stop_session(session)

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)


def container_start(request):
    assert isinstance(request, HttpRequest)
    notebook_id = request.GET['notebook_id']
    notebook = Notebook.objects.filter(id=notebook_id)[0]
    username = request.user.username
    
    
    spawner = Spawner(username)
    spawner.start_notebook(notebook)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def container_stop(request):
    assert isinstance(request, HttpRequest)
    notebook_id = request.GET['notebook_id']
    notebook = Notebook.objects.filter(id=notebook_id)[0]
    username = request.user.username
    spawner = Spawner(username)
    spawner.stop_notebook(notebook)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)


def container_delete(request):
    assert isinstance(request, HttpRequest)
    notebook_id = request.GET['notebook_id']
    notebook = Notebook.objects.filter(id=notebook_id)[0]
    username = request.user.username
    spawner = Spawner(username)
    spawner.delete_notebook(notebook)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_open(request):
    assert isinstance(request, HttpRequest)
    repo_name = request.GET['repo']
    repo = Repo(request.user.username, repo_name)
    if not repo.is_local_existing():
        repo.clone()

    assert isinstance(request, HttpRequest)
    project_owner = request.GET['project_owner']
    project_name = request.GET['project_name']
    description = request.GET['description']
    project_id = request.GET['project_id']
    g = Gitlab(request)
    project_image = g.get_project_variable(project_id, 'container_image')
    username = request.user.username
    spawner = Spawner(username,project_owner, project_name, image=project_image)
    notebook = spawner.ensure_notebook_running()
    jupyter = Jupyter(notebook)

    notebook_path = LibBase.join_path('projects/',repo_name)

    is_forked = eval(request.GET['is_forked'])
    if is_forked:
        project_id = int(request.GET['project_id'])
        target_id = int(request.GET['target_id'])
        session = spawner.start_session(notebook_path, 'python3', repo_name, notebook.name, is_forked, project_id, target_id)
    else:
        session = spawner.start_session(notebook_path, 'python3', repo_name, notebook.name)
    url = session.external_url
    return HttpResponseRedirect(url)

def notebooks_clone(request):
    assert isinstance(request, HttpRequest)
    repo_name = request.GET['repo']
    repo = Repo(request.user.username, repo_name)
    if not repo.is_local_existing():
        repo.clone()

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)


def notebooks_pull_confirm(request):
    assert isinstance(request, HttpRequest)
    repo_name = request.GET['repo']
    repo = Repo(request.user.username, repo_name)
    print(repo_name)
    # Popup ablak kell
    repo.ensure_local_dir_empty()
    repo.clone()

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    
def notebooks_change_image(request):
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    project_image = request.POST['project.image']
    print("PP",project_id,project_image)
    g = Gitlab(request)
    g.change_variable_value(project_id,'container_image',project_image)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)



def notebooks_commit(request):
    assert isinstance(request, HttpRequest)
    notebook_path_dir = request.GET['notebook_path_dir']
    is_forked = request.GET['is_forked']
    project_owner = request.GET['project_owner']
    project_name = request.GET['project_name']
    repo = Repo(request.user.username, notebook_path_dir)
    committable_dict = repo.list_committable_files(
        project_owner, project_name)
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
            'project_owner' : project_owner,
            'project_name' : project_name,
            'committable_dict' : committable_dict,
        })
    )

def notebooks_commitform(request):
    assert isinstance(request, HttpRequest)
    notebook_path_dir = request.POST['notebook_path_dir']
    message = request.POST['message']
    is_forked = request.POST['is_forked']
    project_owner = request.POST['project_owner']
    project_name = request.POST['project_name']
    modified_files = request.POST['modified_files']
    modified_file_list = []
    if(modified_files != ''):
        modified_files = modified_files.replace("'", "")
        modified_file_list = modified_files.split(',')
    deleted_files = request.POST['deleted_files']
    deleted_file_list = []
    if(deleted_files != ''):
        deleted_files = deleted_files.replace("'", "")
        deleted_file_list = deleted_files.split(',')
    next_page = HUB_NOTEBOOKS_URL
    repo = Repo(request.user.username, notebook_path_dir)
    repo.commit_and_push(message, request.user.email, project_owner, project_name,
                         modified_file_list, deleted_file_list)
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
    url(r'^/new$', project_new, name='project-new'),
    url(r'^/shutdown$', notebooks_shutdown, name='notebooks-shutdown'),
    url(r'^/start', container_start, name='container-start'),
    url(r'^/stop', container_stop, name='container-stop'),
    url(r'^/delete$', container_delete, name='container-delete'),
    #url(r'^/containershutdown$', container_shutdown, name='container-shutdown'),
    url(r'^/open$', notebooks_open, name = 'notebooks-open'),
    url(r'^/clone$', notebooks_clone, name = 'notebooks-clone'),
    url(r'^/pull-confirm$', notebooks_pull_confirm, name = 'notebooks-pull-confirm'),
    url(r'^/change-image$', notebooks_change_image, name = 'notebooks-change-image'),
    url(r'^/commit$', notebooks_commit, name='notebooks-commit'),
    url(r'^/commitform$', notebooks_commitform, name='notebooks-commitform'),
    url(r'^/mergerequestform$', notebooks_mergerequestform, name='notebooks-mergerequestform'),
    url(r'^/mergerequestlist', notebooks_mergerequestlist, name='notebooks-mergerequestlist'),
    url(r'^/acceptmergerequest', notebooks_acceptmergerequest, name='notebooks-acceptmergerequest'),
    url(r'^/fork$', project_fork, name = 'project-fork'),
]