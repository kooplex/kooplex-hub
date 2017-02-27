import os.path
import re

from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect,HttpResponse
from django.template import RequestContext
from django.template.response import TemplateResponse
from datetime import datetime
import json

from kooplex.lib.libbase import get_settings
from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session
from kooplex.lib.libbase import LibBase
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.lib.dashboards import Dashboards
from kooplex.lib.repo import Repo
from kooplex.lib.spawner import Spawner
from kooplex.lib.jupyter import Jupyter
from kooplex.lib.smartdocker import Docker
import git

NOTEBOOK_DIR_NAME = 'notebooks'
HUB_NOTEBOOKS_URL = '/hub/notebooks'

from kooplex.lib.debug import *

def notebooks(request,errors=[] ):
    """Renders the notebooks page"""
    print_debug("Rendering notebook page")

    assert isinstance(request, HttpRequest)

    username = request.user.username
    
    print_debug("Rendering notebook page, getting sessions")
    notebooks = Notebook.objects.filter(username=username)
    sessions = []
    for n in notebooks:
        ss = Session.objects.filter(notebook=n)
        for s in ss:
            sessions.append(s)
    print_debug("Rendering notebook page, projects from gitlab")
    g = Gitlab(request)
    projects, unforkable_projectids = g.get_projects()
    print(projects)
    if type(projects) != dict:
    #A redirect to homepage
#    if type(projects) == dict:
#        return render(request,
#        'app/index.html',
#        context_instance = RequestContext(request,
#        { 'title':'Home Page','year':datetime.now().year,})
#        )

        print_debug("Rendering notebook page, project variables from gitlab")
        for project in projects:
            variables = g.get_project_variables(project['id'])
            project['commits'] =  g.get_repository_commits(project['id'])
            new_variables={}
            if 'message' not in variables:
                for  var in variables:
                    new_variables[var['key']] = var['value']
                project['variables']=new_variables

    print_debug("If something is odd, may you forgot to init hub, otherwise no error comes here :|")
	    #TODO: get uid and gid from projects json
    print_debug("Rendering notebook page, unforkable project  from gitlab")
    gadmin = GitlabAdmin(request)
    public_projects = gadmin.get_all_public_projects(unforkable_projectids)
    for project in public_projects:
            variables = gadmin.get_project_variables(project['id'])
            new_variables={}
            if 'message' not in variables:
                for  var in variables:
                    new_variables[var['key']] = var['value']
                project['variables']=new_variables

    print_debug("Rendering notebook page, images from docker")

    d = Docker()
    notebook_images = d.get_allnotebook_images()

    for project in projects:
        for session in sessions:
            if project['id']==session.project_id:
                project['running']=True
                project['session'] = session
                project['notebook'] = session.notebook
                break
            else:
                project['running'] = False


    # TODO unittest to check if port is accessible (ufw allow "5555")
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
            'errors' : errors,
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
    description = request.POST['project.description']
    print_debug("Creating new project, create in gitlab")

    unwanted_characters = re.compile('[a-z]([0-9]|[a-z]|-)*')
    matchObj = unwanted_characters.match(project_name)
    try:
        if matchObj.end()!=len(project_name):
            raise IndexError
    except:
        return notebooks(request,errors=['UseOnlyLowerLetters'])  #,description=description)


    g = Gitlab(request)
    message_json = g.create_project(project_name,public,description)
    res = g.get_project_by_name(project_name)
    if len(res)>1:
        print("Warning to the log: there more than 1 project which is not acceptable!!!!")
        for project in res:
            if project_name==project['name']:
                project_id=project['id']
                break
    else:
        project_id=res[0]['id']

    print_debug("Creating new project, add variables in gitlab")
    #add image_name to project
    g.create_project_variable(project_id,'container_image', project_image_name)
    g.create_project_variable(project_id, 'notebook', 'True')

    #Create a README
    g.create_project_readme(project_id,"README.md","* proba","Created a default README")
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

def project_delete(request):
    assert isinstance(request, HttpRequest)
    print_debug("Delettning project, ")

    project_id = request.GET['project_id']
    g = Gitlab(request)
    message_json = g.delete_project(project_id)
    if message_json:
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
    print_debug("Starting container")

    notebook_id = request.GET['notebook_id']
    notebook = Notebook.objects.filter(id=notebook_id)[0]
    username = request.user.username
    
    print_debug("Starting container,Spawning")    
    spawner = Spawner(username)
    spawner.start_notebook(notebook)
    print_debug("Starting container, Finished")
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def container_stop(request):
    assert isinstance(request, HttpRequest)
    print_debug("Stopping container,")

    notebook_id = request.GET['notebook_id']
    notebook = Notebook.objects.filter(id=notebook_id)[0]
    username = request.user.username
    spawner = Spawner(username)
    spawner.stop_notebook(notebook)
    print_debug("Starting container, Finished")

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)


def container_delete(request):
    assert isinstance(request, HttpRequest)
    print_debug("Deleting container,")

    notebook_id = request.GET['notebook_id']
    notebook = Notebook.objects.filter(id=notebook_id)[0]
    username = request.user.username
    spawner = Spawner(username)
    spawner.delete_notebook(notebook)
    print_debug("Starting container, Finished")
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_open(request):
    assert isinstance(request, HttpRequest)
    print_debug("Opening session,")
    repo_name = request.GET['repo']
    repo = Repo(request.user.username, repo_name)
    if not repo.is_local_existing():
        repo.clone()

    assert isinstance(request, HttpRequest)
    project_owner = request.GET['project_owner']
    project_name = request.GET['project_name']
    project_id = request.GET['project_id']
    print_debug("Opening session, gitlab")
    g = Gitlab(request)
    project_image = g.get_project_variable(project_id, 'container_image')
    username = request.user.username
    print_debug("Opening session, spawning")
    spawner = Spawner(username,project_owner, project_name, image=project_image)
    notebook = spawner.ensure_notebook_running()
    jupyter = Jupyter(notebook)

    notebook_path = LibBase.join_path('projects/',repo_name)
    print("YYY", notebook_path)
    is_forked = eval(request.GET['is_forked'])
    if is_forked:
        project_id = int(request.GET['project_id'])
        target_id = int(request.GET['target_id'])
        session = spawner.start_session(notebook_path, 'python3', repo_name, notebook.name, is_forked, project_id, target_id)
    else:
        session = spawner.start_session(notebook_path, 'python3', repo_name, notebook.name,project_id=project_id)
    url = session.external_url
    print_debug("Opening session, Finished")
    #return HttpResponseRedirect(url)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_clone(request):
    assert isinstance(request, HttpRequest)
    print_debug("Cloning project,")
    repo_name = request.GET['repo']
    repo = Repo(request.user.username, repo_name)
    if not repo.is_local_existing():
        repo.clone()

    print_debug("Cloning project, Finished")
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_deploy_api(request):
    assert isinstance(request, HttpRequest)
    print_debug("Deploying notebook,")
    project_name = request.GET['project_name']
    project_owner = request.GET['project_owner']
    home_dir = get_settings('users', 'home_dir', None, '')
    file = LibBase.join_path(home_dir,'projects')
    file = LibBase.join_path(file, project_owner)
    file = LibBase.join_path(file, project_name)
    file = LibBase.join_path(file, 'index.ipynb')
    print(file)
    d = Dashboards()
    res2 = d.deploy(project_name,file)
    print(res2.json())
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_deploy(request):
    assert isinstance(request, HttpRequest)
    print_debug("Deploying notebook,")
    project_name = request.GET['project_name']
    project_owner = request.GET['project_owner']
    project_id = request.GET['project_id']
    username = request.user.username
    srv_dir = get_settings('users', 'srv_dir', None, '')
    file = LibBase.join_path(srv_dir,'home')
    file = LibBase.join_path(file,username)
    file = LibBase.join_path(file,'projects')
    file = LibBase.join_path(file, project_owner)
    file = LibBase.join_path(file, project_name)
    file = LibBase.join_path(file, 'index.ipynb')
    print(file)
    g=Gitlab(request)
    g.create_project_variable(project_id, 'worksheet', 'True')
    d = Dashboards()
    res2 = d.deploy(username, project_owner, project_name, file)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_view_deploy(request):
    """Not used """
    assert isinstance(request, HttpRequest)
    print_debug("Deploying notebook,")
    project_name = request.GET['project_name']
    project_owner = request.GET['project_owner']
    project_id = request.GET['project_id']
    username = request.user.username
    srv_dir = get_settings('users', 'srv_dir', None, '')
    file = LibBase.join_path(srv_dir,'home')
    file = LibBase.join_path(file,username)
    file = LibBase.join_path(file,'projects')
    file = LibBase.join_path(file, project_owner)
    file = LibBase.join_path(file, project_name)
    file = LibBase.join_path(file, 'index.ipynb')
    g=Gitlab(request)
    g.create_project_variable(project_id, 'worksheet', 'True')
    d = Dashboards()
    res2 = d.deploy(username, project_owner, project_name, file)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_prepare_to_convert_html(request):
    """Lists files """
    assert isinstance(request, HttpRequest)
    notebook_path = request.GET['notebook_path']
    project_owner = request.GET['project_owner']
    project_name = request.GET['project_name']
    project_id = request.GET['project_id']
    notebook_id = request.GET['notebook_id']
    container_name = request.GET['container_name']   #SHOULD DO OTHERWAY!!!!
    srv_dir=get_settings('users', 'srv_dir')
    home_dir = get_settings('users', 'home_dir')
    home_dir = home_dir.replace('{$username}', project_owner)
    notebook_path_dir = LibBase.join_path(home_dir, notebook_path)
    local_path_dir = LibBase.join_path(srv_dir, notebook_path_dir)

    files = os.listdir(local_path_dir)
    ipynbs=[]; other_files=[]
    for file in files:
        if file[-5:]=="ipynb":
            ipynbs.append(file)
        else:
            if file[0]!=".":
                other_files.append(file)

    return render(
        request,
        'app/todeploy.html',
        context_instance=RequestContext(request,
        {
            'notebook_path_dir': notebook_path_dir,
            'ipynbs': ipynbs,
            'other_files': other_files,
            'project_id': project_id,
            'project_owner' : project_owner,
            'project_name' : project_name,
            'notebook_id' : notebook_id,
        })
    )

def notebooks_publish(request):
    """ Converts ipynb to html in the opened container, creates variable in gitlab, commits file in gitlab"""
    assert isinstance(request, HttpRequest)
    print_debug("Deploying notebook,")
    project_name = request.POST['project_name']
    project_owner = request.POST['project_owner']
    username = request.user.username
    project_id = request.POST['project_id']
    notebook_path_dir = request.POST['notebook_path_dir']
    ipynb_files = request.POST['ipynb_files']
    other_files = request.POST['other_files']
    notebook_id = request.POST['notebook_id']
    g=Gitlab(request)
    notebook = Notebook.objects.filter(id=notebook_id)[0]
    ipynb_files=ipynb_files.split(",")
    other_files=other_files.split(",")

    project = g.get_project_by_name(project_name)[0]

    dashb = Dashboards()
    if 'html' in request.POST.keys() and ipynb_files[0]!="'":
        docli = Docker()
        for ipynb in ipynb_files:
            file = ipynb[:-6]
            command=" jupyter-nbconvert --to html /%s/%s " %(notebook_path_dir,ipynb)
            docli.exec_container(notebook, command, detach=False)

            dashb.deploy_html(username, project_owner, project_name, request.user.email, notebook_path_dir, file+".html")
            g.create_project_variable(project_id, 'worksheet_%s'%file, file + ".html")

    elif 'dashboard' in request.POST.keys():
        for file in ipynb_files:
            dashb.deploy_data(project, notebook_path_dir, file)
            g.create_project_variable(project_id, 'dashboard_%s'%file[:-6], notebook.image)

    if other_files[0] != "'":
        for file in other_files:
            dashb.deploy_data(project, notebook_path_dir, file)

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_pull_confirm(request):
    assert isinstance(request, HttpRequest)
    print_debug("Reverting project,")
    repo_name = request.GET['repo']
    repo = Repo(request.user.username, repo_name)
    # Popup ablak kell
    repo.ensure_local_dir_empty()
    repo.clone()
    print_debug("Reverting project, Finished")

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    
def notebooks_revert(request):
    assert isinstance(request, HttpRequest)
    print_debug("Reverting project,")
    repo_name = request.GET['repo']
    repo = Repo(request.user.username, repo_name)
    print(repo_name)
    # Popup ablak kell
    repo.ensure_local_dir_empty()
    repo.clone()
    print_debug("Reverting project, Finished")

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    
    
def notebooks_change_image(request):
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    project_image = request.POST['project.image']
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
#    repo.commit_and_push(message, request.user.email, project_owner, project_name,
#                         modified_file_list, deleted_file_list)
    repo.commit_and_push_default(message, request.user.email, project_owner, project_name)
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
    #TODO gadmin get image variable
    print_debug(message)
    gadmin = GitlabAdmin(request)
    forked_project_image = gadmin.get_project_variable(itemid, 'container_image')
    forked_project = gadmin.get_project(itemid)
    project = g.get_project_by_name(forked_project['name'])
    g.change_variable_value(project[0]['id'], 'container_image', forked_project_image)
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
    url(r'^/deploy$', notebooks_deploy, name = 'notebooks-deploy'),
    url(r'^/viewdeploy$', notebooks_view_deploy, name = 'notebooks-view-deploy'),
    url(r'^/preparetoconverthtml$', notebooks_prepare_to_convert_html, name = 'notebooks-prepare-to-convert-html'),
    url(r'^/converthtml$', notebooks_publish, name = 'notebooks-convert-html'),
    url(r'^/pull-confirm$', notebooks_pull_confirm, name = 'notebooks-pull-confirm'),
    url(r'^/change-image$', notebooks_change_image, name = 'notebooks-change-image'),
    url(r'^/delete-project$', project_delete, name = 'notebooks-delete-project'),
    url(r'^/commit$', notebooks_commit, name='notebooks-commit'),
    url(r'^/commitform$', notebooks_commitform, name='notebooks-commitform'),
    url(r'^/mergerequestform$', notebooks_mergerequestform, name='notebooks-mergerequestform'),
    url(r'^/mergerequestlist', notebooks_mergerequestlist, name='notebooks-mergerequestlist'),
    url(r'^/acceptmergerequest', notebooks_acceptmergerequest, name='notebooks-acceptmergerequest'),
    url(r'^/fork$', project_fork, name = 'project-fork'),
]