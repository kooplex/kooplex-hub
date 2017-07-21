import os.path
import re
#from urllib.request import urlopen

from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect,HttpResponse
from django.template import RequestContext
from django.template.response import TemplateResponse
import logging
import logging.config
from datetime import datetime
import json

import pwgen

from kooplex.lib.libbase import get_settings
from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session
from kooplex.hub.models.project import Project
from kooplex.hub.models.mountpoints import MountPoints, MountPointProjectBinding, MountPointPrivilegeBinding
from kooplex.hub.models.volume import Volume, VolumeProjectBinding
from kooplex.hub.models.dockerimage import DockerImage
from kooplex.hub.models.report import Report
from kooplex.hub.models.user import HubUser
from kooplex.hub.models.dashboard_server import Dashboard_server
from django.contrib.auth.models import User

from kooplex.lib.libbase import LibBase
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.lib.repo import Repo
from kooplex.lib.spawner import Spawner
from kooplex.lib.ocspawner import OCSpawner
from kooplex.lib.jupyter import Jupyter
from kooplex.lib.smartdocker import Docker
from kooplex.lib.sendemail import send_new_password
import git

NOTEBOOK_DIR_NAME = 'notebooks'
HUB_NOTEBOOKS_URL = '/hub/notebooks'

from kooplex.lib.debug import *


def notebooks(request,errors=[], commits=[] ):
    """Renders the notebooks page"""
    print_debug("Rendering notebook page")
    logger = logging.getLogger(__name__)

    assert isinstance(request, HttpRequest)

    user = request.user
    hubuser = HubUser.objects.get(username = user.username)

    print_debug("Rendering notebook page, getting sessions")
    notebooks = Notebook.objects.filter(username = user.username)
 #   sessions = []
    running = []
    for n in notebooks:
        ss = Session.objects.filter(notebook = n)
        for s in ss:
 #           sessions.append(s)
            running.append(s.project_id)

    print_debug("Rendering notebook page, projects from gitlab")

    all_projects = Project.objects.all()
    shared_with_me_projects = [ project for project in all_projects for i in project.gids.split(",") if i  and int(i) == hubuser.gitlab_id ]

    access_error=[]

	#TODO: get uid and gid from projects json
    print_debug("Rendering notebook page, unforkable project  from gitlab")
    public_projects = Project.objects.filter(visibility = "public").exclude(owner_username = user.username)

    print_debug("Rendering notebook page, images from docker")

    notebook_images = [ image.name for image in DockerImage.objects.all() ]

    bindings = [ mppb for mppb in MountPointPrivilegeBinding.objects.filter(user = hubuser) ]
    volumes = Volume.objects.all()

    ocspawner = OCSpawner(hubuser)
    oc_running = ocspawner.state_ == 'running'

    # TODO unittest to check if port is accessible (ufw allow "5555")
    return render(
        request,
        'app/notebooks.html',
        context_instance = RequestContext(request,
        {
            'notebooks': notebooks,
            'running': running,
            'shared_with_me_projects': shared_with_me_projects,
            'commits': commits,
            'public_projects': public_projects,
            'user': user,
            'notebook_dir_name': NOTEBOOK_DIR_NAME,
            'notebook_images' : notebook_images,
            'errors' : errors,
            'access_error' : access_error,
            'oc_running': oc_running,
            'netrc_exists': hubuser.file_netrc_exists_,
            'bindings': bindings,
            'volumes': volumes,
        })
    )

def project_new(request):
    assert isinstance(request, HttpRequest)
    ooops = []
    project_name = request.POST['project_name'].strip()
#TODO: nicer regexp
    if not re.match(r'^[a-zA-Z]([0-9]|[a-zA-Z]|-|_| )*$', project_name):
        ooops.append('For project name specification please use only Upper/lower case letters, hyphens, spaces and underscores.')
    description = request.POST['project_description'].strip()
#FIXME: regexp
#    if not re.match(r'^[a-zA-Z]([0-9]|[a-zA-Z]|-|_| |\n)*$', description):
#        ooops.append('In your project description use only Upper/lower case letters, hyphens, spaces and underscores.')
    if len(ooops):
        return notebooks(request, errors = ooops)
    scope = request.POST['button']
    template = request.POST['project_template']

    if template.startswith('clonable_project='):
        return notebooks(request, errors = [ 'This part of the code is not implemented yed.' ])
        # project_image_name =
    elif template.startswith('image='):
        project_image_name = template.split('=')[-1]

    # parse shares and volumes
    mp = []
    mprw = []
    vols = []
    for k, v in request.POST.items():
        if re.match('^mp=\d+', k):
            mp.append(int(v))
        elif re.match('^mprw=\d+', k):
            mprw.append(int(v))
        elif re.match('^vol=', k):
            V = Volume.objects.filter(name = v)[0]  #FIXME: use id here and sg like get
            vols.append(V)

#FIXME: PREPARE THE APPROPRIATE GIT FOLDER HERE: image= case: git clone, clonable_project= case: git clone the 2, copy files, git add, git push, rm temp
    g = Gitlab(request)
    print_debug("Creating new project, add variables")
    try:
        message_json = g.create_project(project_name, scope, description)
        if len(message_json):
            raise Exception(message_json)
#FIXME: check failure
        res = g.get_project_by_name(project_name)
        p = Project()
        p.init(res[0])
        m = g.get_project_members(p.id)
        p.from_gitlab_dict_projectmembers(m)
    
        #Add image_name to project
        p.image = project_image_name
        p.save()

        # manage shares
        while len(mp):
            mpid = mp.pop()
            mpb = MountPointProjectBinding()
            mpb.project = p
            mpb.mountpoint = MountPoints.objects.get(id = mpid)
            mpb.readwrite = mpid in mprw
            mpb.save()

        # manage volumes
        while len(vols):
            vol = vols.pop()
            vpb = VolumeProjectBinding(volume = vol, project = p)
            vpb.save()

        #Create a README (FIXME only for empty)
        g.create_project_readme(p.id, "README.md", "* proba", "Created a default README")
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    except Exception as e:
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
                                            {
                                                'error_title': 'Error',
                                                'error_message': str(e),
                                            })
        )

def project_delete(request):
    assert isinstance(request, HttpRequest)
    print_debug("Delettning project, ")

    project_id = request.GET['project_id']
    g = Gitlab(request)
    message_json = g.delete_project(project_id)
    if message_json:
        project = Project.objects.get(id=project_id)
        project.delete()
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

def container_start(request):
    assert isinstance(request, HttpRequest)
    print_debug("Opening session,")
    project_id = request.GET['project_id']
    project = Project.objects.get(id=project_id)

#obsoleted by notebook startup script
#    repo = Repo(request.user.username, project.path_with_namespace)
#    if not repo.is_local_existing():
#        repo.clone()

    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    project = Project.objects.get(id=project_id)
    print_debug("Opening session, gitlab")
    username = request.user.username
    print_debug("Opening session, spawning")
    spawner = Spawner(username, project, image=project.image)
    notebook = spawner.ensure_notebook_running()
    #jupyter = Jupyter(notebook)

    notebook_path = LibBase.join_path('projects/',project.path_with_namespace)
    print("YYY", notebook_path)
    #is_forked = eval(request.GET['is_forked'])
    #if is_forked:
    #    target_id = int(request.GET['target_id'])
    #    session = spawner.start_session(notebook_path, 'python3', project.path_with_namespace, notebook.name, is_forked, project.id, target_id)
    #else:
    #    session = spawner.start_session(notebook_path, 'python3', project.path_with_namespace, notebook.name, project_id=project.id)
    session = spawner.start_session(notebook_path, 'python3', project.path_with_namespace, notebook.name,
                                    project_id=project.id)

    #project.session = session
    #project.save()
    session.project_id = project.id
    session.save()
    print_debug("Opening session, Finished")
    #return HttpResponseRedirect(url)
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def container_open(request):
    assert isinstance(request, HttpRequest)
    print_debug("Redirect to notebook server")
    user = request.user
    project_id = request.GET['project_id']
    notebooks = Notebook.objects.filter(username = user.username, project_id = project_id)
    assert len(notebooks) == 1
    session = Session.objects.get(notebook = notebooks[0])
    url_w_token = session.external_url + '/?token=aiSiga1aiFai2AiZu1veeWein5gijei8yeLay2Iecae3ahkiekeisheegh2ahgee'
    return HttpResponseRedirect(url_w_token)

def container_delete(request):
    assert isinstance(request, HttpRequest)
    print_debug("Deleting container,")
    username = request.user.username
    project_id = request.GET['project_id']

    project = Project.objects.get(id=project_id)
    #notebook_id = project.session.notebook.id
    #session = Session.objects.get(project_id=project_id,notebook.username=username)
     #= Session.objects.get(project_id=project_id,notebook.username=username)
    #notebook_id = session.notebook.id
    notebook = Notebook.objects.filter(username=username, project_name=project.name)[0]

    spawner = Spawner(username, project)
    spawner.delete_notebook(notebook)
    # Change/Save project status
    #project.session = None
    #project.save()

    print_debug("Starting container, Finished")
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

def notebooks_publishform(request):
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    project = Project.objects.get(id = project_id)
    folder = project.gitdir(username = request.user.username)
    files = os.listdir(folder)

    ipynbs = [];
    other_files = []
    for file in files:
        if file[-5:] == "ipynb":
            ipynbs.append(file)
        else:
            if file[0] != ".":
                other_files.append(file)

    return render(
        request,
        'app/notebooks-publishform.html',
        context_instance=RequestContext(request,
                                        {
                                            'ipynbs': ipynbs,
                                            'other_files': other_files,
                                            'project_id': project_id,
                                        })
    )

def notebooks_publish(request):
    """ Converts ipynb to html in the opened container, creates variable in gitlab, commits file in gitlab"""
    assert isinstance(request, HttpRequest)
    if 'cancel' in request.POST.keys():
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    print_debug("Deploying notebook,")

    username = request.user.username
    project_id = request.POST['project_id']
    if 'html' in request.POST.keys():
        type = 'html'
    if 'dashboard' in request.POST.keys():
        type = 'dashboard'

    # TODO here and elsewhere: does the filter give more than 1?
    project = Project.objects.get(id = project_id)

    ipynb_file = request.POST['ipynb_file']
    other_files = request.POST.getlist('other_files')
    prefix = get_settings('prefix', 'name', None, '')
    image_type = project.image.split(prefix + "-notebook-")[1]

    try:
        dashboard_server = Dashboard_server.objects.get(type = image_type)
        creator = HubUser.objects.get(username = request.user.username)
        report = Report()
        report.init(dashboard_server, project, creator, file = ipynb_file, type = type)
        report.deploy(other_files)
        report.scope = request.POST['scope']
        report.save()

        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    except Exception as e:
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
                                            {
                                                'error_title': 'Error',
                                                'error_message': str(e),
                                            })
        )

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

def Refresh_database(request):

    # Get Docker image names
    d = Docker()
    notebook_images = d.get_all_notebook_images()
    for image in notebook_images:
        i = DockerImage()
        i = i.from_docker_dict(image)
        i.save()
        dashboards_prefix = get_settings('dashboards', 'prefix', None, '')
        notebook_prefix = get_settings('prefix', 'name', None, '')
        dashboard_container_name = dashboards_prefix + "_dashboards-" + i.name.split(notebook_prefix + "-notebook-")[1]
        docker_container = d.get_container(dashboard_container_name, original=True)
        #container, docker_container = d.get_container(dashboard_container_name)
        if docker_container:
            D = Dashboard_server()
            D.init(d, docker_container)
            D.save()

    g = Gitlab()
    gitlab_projects = g.get_my_projects()
    gitlab_projects = []
    for gitlab_project in gitlab_projects:
        p = Project()
        p.init(gitlab_project)
        m = g.get_project_members(p.id)
        p.from_gitlab_dict_projectmembers(m)
        p.save()
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_revert(request):
    assert isinstance(request, HttpRequest)
    if 'cancel' not in request.POST.keys():
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
    project = Project.objects.get(id=project_id)
    project.image = request.POST['project.image']
    project.save()
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def Refresh_project(request):
    project_id = request.GET['project_id']
    username = request.user.username
    project = Project.objects.get(id=project_id)
    project_commits = {}
    g = Gitlab(request)
    commits = g.get_repository_commits(project.id)
    project_commits[project.id] = commit_style(commits)
    project_commits[project.id]['committable_dict'] = Collect_commitables(username, project.name, project.owner_username, project.path_with_namespace)

    return notebooks(request, commits=project_commits)

def commit_style(commits):
    for commit in commits:
        if "committed_date" in commit.keys():
            commit['kdate'] = commit['committed_date'][:10]
            commit['ktime'] = commit['committed_date'][11:19]
        elif "created_at" in commit.keys():
            commit['kdate'] = commit['created_at'][:10]
            commit['ktime'] = commit['created_at'][11:19]
        else:
            commit['kdate'] = "NULL"
            commit['ktime'] = "NULL"

        # commit['ktime_zone']=commit['committed_date'][-6:]
        commit['ktime_zone'] = 'CET'

    return commits

def notebooks_revertform(request):
    project_id = request.GET['project_id']
    project = Project.objects.get(id=project_id)
    g = Gitlab(request)
    commits = g.get_repository_commits(project.id)
    commits = commit_style(commits)
    return render(
        request,
        'app/notebooks-revertform.html',
        context_instance=RequestContext(request,
        {
            'project': project,
            'commits' : commits,
        })
    )


def notebooks_commitform(request):
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    target_id = 0
    username = request.user.username
    project = Project.objects.get(id=project_id)

    try:
        repo = Repo(username, project.path_with_namespace)
        committable_dict = repo.list_committable_files(project.path_with_namespace)
        print("committable", committable_dict)
    except:
        committable_dict = []

    return render(
        request,
        'app/notebooks-commitform.html',
        context_instance=RequestContext(request,
        {
            'project': project,
            'target_id': target_id,
            'committable_dict' : committable_dict,
        })
    )

def notebooks_commit(request):
    assert isinstance(request, HttpRequest)
    if 'cancel' in request.POST.keys():
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

    project_id = int(request.POST['project_id'])
    project = Project.objects.get(id=project_id)
    message = request.POST['message']
    is_forked = False #request.POST['is_forked']

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
    repo = Repo(request.user.username, project.path_with_namespace)
    repo.commit_and_push(message, request.user.email, project.owner_username, project.name, project.creator_name,
                         modified_file_list, deleted_file_list)
#    repo.commit_and_push_default(message, request.user.email, project_owner, project_name)
    # TODO megcsinalni ezt is
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

def usermanagementForm(request):
    users = filter(lambda x: x.username != 'gitlabadmin', User.objects.all())
    return render(
        request,
        'app/usermanagement.html',
        context_instance=RequestContext(request,
        { 'users': users,
          'user': request.user })
    )


from kooplex.lib.ldap import Ldap
import subprocess
from distutils.dir_util import mkpath


#FIXME: put functionality in HubUser model
class myuser:

    def __init__(self):
        self._data = dict( [ (k, None) for k in ['firstname', 'lastname', 'username', 'email', 'password', 'is_superuser'] ])

    def __str__(self):
        return str(self._data)

    def __getitem__(self, k):
        if not k in self._data:
            raise Exception("Unknown attribute %s" % k)
        if self._data[k] is None:
            raise Exception("Unset attribute %s" % k)
        return self._data[k]
    

    def setattribute(self, **kw):
        for k, v in kw.items():
            if not k in self._data.keys():
               raise Exception("Unknown attribute: %s" % k)
            self._data[k] = v

    def create(self):
        def mkdir(d, uid = 0, gid = 0, mode = 0b111101000):
            mkpath(d)
            os.chown(d, uid, gid)
            os.chmod(d, mode) 

        ooops = []
        dj_user = HubUser(
            username = self['username'],
            password = self['password'],
            first_name = self['firstname'],
            last_name = self['lastname'],
            email = self['email'],
            is_superuser = self['is_superuser']
        )
        dj_user.home = "/home/" + self['username'] #FIXME: this is ugly
        l = Ldap()
        try:
            dj_user = l.add_user(dj_user) # FIXME:
        except Exception as e:
            ooops.append("ldap: %s" % e)

        gad = GitlabAdmin()
        try:
            msg = gad.create_user(self)
            if len(msg):
                ooops.append("gitcreate: %s" % msg)
        except Exception as e:
            ooops.append("gitcreate2: %s" % e)

        gg = gad.get_user(dj_user.username)[0]
        dj_user.gitlab_id = gg['id']

        srv_dir = get_settings('users', 'srv_dir', None, '')
        home_dir = get_settings('users', 'home_dir', None, '')
        home_dir = os.path.join(srv_dir, home_dir.replace('{$username}', self['username']))
        ssh_dir = os.path.join(home_dir, '.ssh')
        oc_dir = os.path.join(srv_dir, '_oc', self['username'])
        git_dir = os.path.join(srv_dir, '_git', self['username'])

        mkdir(home_dir, uid = dj_user.uid, gid = dj_user.gid)
        mkdir(ssh_dir, uid = dj_user.uid, gid = dj_user.gid, mode = 0b111000000)
        mkdir(oc_dir, uid = dj_user.uid, gid = dj_user.gid, mode = 0b111000000)
        mkdir(git_dir, uid = dj_user.uid, gid = dj_user.gid)

        key_fn = os.path.join(ssh_dir, "gitlab.key")
        subprocess.call(['/usr/bin/ssh-keygen', '-N', '', '-f', key_fn])
        os.chown(key_fn, dj_user.uid, dj_user.gid)
        os.chown(key_fn + ".pub", dj_user.uid, dj_user.gid)
        key = open(key_fn + ".pub").read().strip()
        
        try:
            msg = gad.upload_userkey(self, key)
            if len(msg):
                ooops.append("gitkeyadd: %s" % msg)
        except Exception as e:
            ooops.append("gitadd2: %s" % e)


        dj_user.save()

        if len(ooops):
            raise Exception(",".join(ooops))

    def pwgen(self):
        pw = pwgen.pwgen(12)
        l = Ldap()
        dj_user = User.objects.get(username = self['username'])
        l.changepassword(dj_user, 'doesntmatter', pw, validate_old_password = False)

        send_new_password(name = "%s %s" % (dj_user.first_name, dj_user.last_name), 
           username = dj_user.username, 
           to = dj_user.email, 
           pw = pw)

    def delete(self):
        ooops = []
        dj_user = User.objects.get(username = self['username'])
        l = Ldap()
        try:
            l.delete_user(dj_user)
        except Exception as e:
            ooops.append("ldap: %s" % e)
        gad = GitlabAdmin()
        try:
            gad.delete_user(self['username'])
        except Exception as e:
            ooops.append("git: %s" % e)
        dj_user.delete()
#TODO: remove appropriate directories from the filesystem
        if len(ooops):
            raise Exception(",RR".join(ooops))

USERMANAGEMENT_URL = '/hub/notebooksusermanagement'
def usermanagement(request):
#FIXME: wrong value
    is_admin = bool(request.POST['isadmin']) if 'isadmin' in request.POST.keys() else False
    U = myuser()
    pw = pwgen.pwgen(12)
    U.setattribute(username = request.POST['username'], 
         firstname = request.POST['firstname'], 
         lastname = request.POST['lastname'], 
         email = request.POST['email'], 
         is_superuser = is_admin,
         password = pw)
    try:
        U.create()
        send_new_password(name = "%s %s" % (request.POST['firstname'], request.POST['lastname']), 
           username = request.POST['username'], 
           to = request.POST['email'], 
           pw = pw)
        return HttpResponseRedirect(USERMANAGEMENT_URL)
    except Exception as e: 
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
            {
                    'error_title': 'Error',
                    'error_message': str(e),
            })
        )

def usermanagement2(request):
    try:
        U = myuser()
        if 'delete' in request.POST:
            U.setattribute(username = request.POST['delete'])
#            U.delete()
        elif 'pwgen' in request.POST:
            U.setattribute(username = request.POST['pwgen'])
            U.pwgen()
        else:
            raise Exception("should not reach this point")
        return HttpResponseRedirect(USERMANAGEMENT_URL)
    except Exception as e: 
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
            {
                    'error_title': 'Error',
                    'error_message': str(e),
            })
        )

def project_membersForm(request):
    me = HubUser.objects.get(username = request.user.username)
    project = Project.objects.get(id = request.GET['project_id'])
    current_members = list( project.members_ )
    current_members.pop( current_members.index(me) )
    allusers = HubUser.objects.all()
    other_users = []
    for user in allusers:
        if user.gitlab_id == 2:
            # skip gitlabadmin
            continue
        if user in current_members:
            continue
        if user == me:
            continue
        other_users.append(user)
    return render(
        request,
        'app/project-members.html',
        context_instance=RequestContext(request,
                                        {
                                            'currentmembers': current_members,
                                            'project': project,
                                            'otherusers': other_users,
                                        })
    )

def project_members_modify(request):
    if  request.POST['button'] == 'Cancel':
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    project = Project.objects.get(id = request.POST['project_id'])
    gids = []
    for k in request.POST.keys():
        try:
            _, gid, _ = re.split('^user_id\[(\d+)\]', k)
            gids.append(int(gid))
        except:
            pass
    if len(gids) == 0:
        # nobody was ticked
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    g = Gitlab()
    ooops = []
    for gid in gids:
        try:
            if request.POST['button'] == 'Add':
                g.add_project_members(project.id, gid)
            elif request.POST['button'] == 'Remove':
                g.delete_project_members(project.id, gid)
        except Exception as e:
            ooops.append(str(e))
    try:
        m = g.get_project_members(project.id)
        project.from_gitlab_dict_projectmembers(m)
        project.save()
    except Exception as e:
        ooops.append(str(e))
    if len(ooops):
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
                                            {
                                                'error_title': 'Error',
                                                'error_message': ",".join(ooops),
                                            })
        )
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def toggle_oc(request):
    assert isinstance(request, HttpRequest)
    try:
        user = request.user
        hubuser = HubUser.objects.get(username = user.username)
        ocspawner = OCSpawner(hubuser)
        if request.POST['button'] == 'Start':
            pw = request.POST['password']
            netrc_exists = request.POST['netrc_exists'] == 'True'
            if not netrc_exists and (len(pw) == 0):
                raise Exception("Please provide a password so the synchronization daemon can access your owncloud storage")

#FIXME: machine name hardcoded
            if len(pw):
                fn_netrc = hubuser.file_netrc_
                netrc = """
machine %s
login %s
password %s
"""     % ('kooplex-nginx', user.username, pw)
                with open(fn_netrc, 'w') as f:
                    f.write(netrc)
                os.chown(fn_netrc, hubuser.uid, hubuser.gid)
                os.chmod(fn_netrc, 0b111000000)
            ocspawner.start()
        elif request.POST['button'] == 'Stop':
            ocspawner.stop()
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    except Exception as e:
        return render(
            request,
            'app/error.html',
            context_instance=RequestContext(request,
                                            {
                                                'error_title': 'Error',
                                                'error_message': str(e),
                                            })
        )



def addvolume(request):
    v = Volume(name = 'tesztvolume')
    resp = v.create()
    return HttpResponse(resp)


urlpatterns = [
    url(r'^$', notebooks, name='notebooks'),
    url(r'^new$', project_new, name='project-new'),
    url(r'^delete_container$', container_delete, name= 'container-delete'),
    url(r'^start_container$', container_start, name = 'container-start'),
    url(r'^open_container$', container_open, name = 'container-open'),
    url(r'^clone$', notebooks_clone, name = 'notebooks-clone'),
    url(r'^preparetoconverthtml$', notebooks_publishform, name = 'notebooks-publishform'),
    url(r'^converthtml$', notebooks_publish, name = 'notebooks-convert-html'),
    url(r'^change-image$', notebooks_change_image, name = 'notebooks-change-image'),
    url(r'^delete-project$', project_delete, name = 'notebooks-delete-project'),
    url(r'^commit$', notebooks_commit, name='notebooks-commit'),
    url(r'^commitform$', notebooks_commitform, name='notebooks-commitform'),
    url(r'^revertform$', notebooks_revertform, name='notebooks-revertform'),
    url(r'^revert$', notebooks_revert, name='notebooks-revert'),
    url(r'^mergerequestform$', notebooks_mergerequestform, name='notebooks-mergerequestform'),
    url(r'^mergerequestlist', notebooks_mergerequestlist, name='notebooks-mergerequestlist'),
    url(r'^acceptmergerequest', notebooks_acceptmergerequest, name='notebooks-acceptmergerequest'),
    url(r'^fork$', project_fork, name='project-fork'),
    url(r'^refresh$', Refresh_database, name='refresh-db'),

    url(r'^usermanagement$', usermanagementForm, name='usermanagement-form'),
    url(r'^adduser$', usermanagement, name='usermanagement-add'),
    url(r'^deleteuser$', usermanagement2, name='usermanagement-delete'),

    url(r'^projectmembersform', project_membersForm, name='project-members-form'),
    url(r'^projectmembersmodify', project_members_modify, name='project-members-modify'),

    url(r'^oc$', toggle_oc, name='oc'),

    url(r'^addvolume$', addvolume, name='addvolume'),
]
