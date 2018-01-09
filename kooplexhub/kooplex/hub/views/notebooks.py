import logging
logger = logging.getLogger(__name__)
debug_logger = logging.getLogger('debug_logger')
info_logger = logging.getLogger('info_logger')
import git
import json
import logging
import logging.config
import os.path
from distutils.dir_util import remove_tree
import pwgen
import re
from datetime import datetime
from django.conf.urls import patterns, url, include
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponseRedirect,HttpResponse
from django.shortcuts import render
from django.template import RequestContext
from django.template.response import TemplateResponse

from kooplex.hub.models.dashboard_server import Dashboard_server
from kooplex.hub.models.dockerimage import DockerImage
from kooplex.hub.models.mountpoints import MountPoints, MountPointProjectBinding, MountPointPrivilegeBinding
from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.project import Project, UserProjectBinding
from kooplex.hub.models.report import Report
from kooplex.hub.models.session import Session
from kooplex.hub.models.user import HubUser
from kooplex.hub.models.volume import Volume, VolumeProjectBinding
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.lib.jupyter import Jupyter
from kooplex.lib.libbase import LibBase
from kooplex.lib.libbase import get_settings,  mkdir

from kooplex.lib.ochelper import OCHelper
from kooplex.lib.repo import Repo  # GONNA BE OBSOLETED
from kooplex.lib.repository import repository
from kooplex.lib.sendemail import send_new_password
from kooplex.lib.smartdocker import Docker
from kooplex.lib.spawner import Spawner

from kooplex.lib.ldap import Ldap
import subprocess

NOTEBOOK_DIR_NAME = 'notebooks'
HUB_NOTEBOOKS_URL = '/hub/notebooks'

from kooplex.lib.debug import *


def notebooks(request, errors = []):
    """Renders the notebooks page"""
    assert isinstance(request, HttpRequest)
    user = request.user
    if user.is_anonymous():
        return HttpResponseRedirect(reverse('login'))

    hubuser = HubUser.objects.get(username = user.username)
    notebooks = Notebook.objects.filter(username = user.username)
    running = []
    for n in notebooks:
        ss = Session.objects.filter(notebook = n)
        for s in ss:
            running.append(s.project_id)

    projects_all = Project.objects.all()
    projects_sharedwithme = sorted([up.project for up in UserProjectBinding.objects.filter(hub_user=hubuser)])
    projects_public = sorted(Project.objects.filter(visibility = "public").exclude(owner_username = user.username))

    notebook_images = [ image.name for image in DockerImage.objects.all() ]

    shares = [ mppb for mppb in MountPointPrivilegeBinding.objects.filter(user = hubuser) ]
    shares_attached = dict( map(lambda p: (p, MountPointProjectBinding.objects.filter( project = p )), projects_sharedwithme) )

    volumes = Volume.objects.all()
    volumes_attached = dict( map(lambda p: (p, [ vpb.volume for vpb in VolumeProjectBinding.objects.filter(project = p) ]), projects_sharedwithme) )

###    ocspawner = OCSpawner(hubuser)
###    oc_running = ocspawner.state_ == 'running'

    # TODO unittest to check if port is accessible (ufw allow "5555")
    return render(
        request,
        'app/notebooks.html',
        context_instance = RequestContext(request,
        {
            'user': user,
            'hubuser': hubuser,  #TODO: atterni
            'notebooks': notebooks,
            'running': running,

            'shared_with_me_projects': projects_sharedwithme,
            'public_projects': projects_public,
            'notebook_dir_name': NOTEBOOK_DIR_NAME,
            'notebook_images' : notebook_images,
            'errors' : errors,
            'oc_running': False, #FIXME: to remove
            'bindings': shares,
            'shares_attached': shares_attached,
            'volumes': volumes,
            'volumes_attached': volumes_attached,
            'year' : 2018,
        })
    )

def parse_shares_and_volumes(request):
    mp = []
    mprw = []
    vols = []
    for k, v in request.POST.items():
        if re.match('^mp=\d+', k):
            mp.append(int(v))
        elif re.match('^mprw=\d+', k):
            mprw.append(int(v))
        elif re.match('^vol=', k):
            V = Volume.objects.get(name = v)
            vols.append(V)
    return mp, mprw, vols

def project_new(request):
    assert isinstance(request, HttpRequest)
    project_name = request.POST['project_name'].strip()
    description = request.POST['project_description'].strip()
    scope = request.POST['button']
    template = request.POST.get('project_template',[])
    # parse shares and volumes
    mp, mprw, vols = parse_shares_and_volumes(request)
    debug_logger.debug("Create project %s - init"% project_name)

    ooops = []
#TODO: nicer regexp
    if not re.match(r'^[a-zA-Z]([0-9]|[a-zA-Z]|-|_| )*$', project_name):
        ooops.append('For project name specification please use only Upper/lower case letters, hyphens, spaces and underscores.')
#FIXME: regexp
#    if not re.match(r'^[a-zA-Z]([0-9]|[a-zA-Z]|-|_| |\n)*$', description):
#        ooops.append('In your project description use only Upper/lower case letters, hyphens, spaces and underscores.')
    if len(ooops):
        return notebooks(request, errors = ooops)
        
    if template:
      if template.startswith('clonable_project='):
        name, owner = template.split('=')[-1].split('@')
        project = Project.objects.get(name = name, owner_username = owner)
        project_image_name = project.image
        # Retrieve former_shares and unify with users current choices
        for mpb in MountPointProjectBinding.objects.filter(project = project):
            mp.append(mpb.id)
        mp = list(set(mp))
        # Retrieve former_volumes and unify with users current choices
        for vpb in VolumeProjectBinding.objects.filter(project = project):
            vols.append(vpb.volume)
        vols = list(set(vols))
        cloned_project = True
      elif template.startswith('image='):
        project_image_name = template.split('=')[-1]
        cloned_project = False
    debug_logger.debug("Create project %s - GitLab"% project_name)

    g = Gitlab(request)
    print_debug("Creating new project, add variables")
    try:
        message_json = g.create_project(project_name, scope, description)
        if len(message_json):
            raise Exception(message_json)
#FIXME: check failure
        res = g.get_project_by_name(project_name)

        debug_logger.debug("Create project %s - Save to Hubdb"% project_name)
        p = Project()
        p.init(res[0])
        p.image = project_image_name
        p.save()

        hubuser = HubUser.objects.get(username = p.owner_username)
        userp = UserProjectBinding()
        userp.set(project = p, hub_user = hubuser)
        userp.save()
        #Add image_name to project
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

        OCHelper(hubuser, p).mkdir()

        if cloned_project:
# Create a magic script to clone ancient projects content
            ancientprojecturl = "ssh://git@%s/%s.git" % (get_settings('gitlab', 'ssh_host'), project.path_with_namespace)
            commitmsg = "Snapshot commit of project %s" % project
            script = """#! /bin/bash
TMPFOLDER=$(mktemp -d)
git clone %(url)s ${TMPFOLDER}
cd ${TMPFOLDER}
rm -rf ./.git/
mv * ~/git/
for hidden in $(echo .?* | sed s/'\.\.'//) ; do
  mv $hidden ~/git
done
cd ~/git
git add --all
git commit -a -m "%(message)s"
git push origin master
rm -rf ${TMPFOLDER}
rm ~/$(basename $0)
            """ % { 'url': ancientprojecturl, 'message': commitmsg }
            home_dir = os.path.join(get_settings('volumes', 'home'), p.owner_username)
            fn_basename = ".gitclone-%s.sh" % p.name
            fn_script = os.path.join(home_dir, fn_basename)
            open(fn_script, 'w').write(script)
            os.chmod(fn_script, 0b111000000)
            hubuser = HubUser.objects.get(username = p.owner_username)
            os.chown(fn_script, int(hubuser.uid), int(hubuser.gid))
        else:
# Create a README file
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

def container_start(request):
    assert isinstance(request, HttpRequest)
    print_debug("Opening session,")
    project_id = request.GET['project_id']
    project = Project.objects.get(id=project_id)
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
    # FIXME: python3 is hardcoded here
    session = spawner.start_session(notebook_path, 'python3', project.path_with_namespace, notebook.name,
                                    project_id=project.id)
    session.project_id = project.id
    session.save()
    print_debug("Opening session, Finished")
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
#FIXME: authorization!
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    project = Project.objects.get(id = project_id)
    reports = Report.objects.filter(project = project)
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
                                            'reports': reports,
                                        })
    )

def notebooks_publish(request):
    """ Converts ipynb to html in the opened container, creates variable in gitlab, commits file in gitlab"""
    assert isinstance(request, HttpRequest)
    if 'cancel' in request.POST.keys():
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    username = request.user.username
    project_id = request.POST['project_id']
    description = request.POST['report_description'].strip()
    if 'html' in request.POST.keys():
        type = 'html'
    elif 'dashboard' in request.POST.keys():
        type = 'dashboard'
    else:
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    project = Project.objects.get(id = project_id)

    ipynb_file = request.POST['ipynb_file']
    other_files = request.POST.getlist('other_files')
    prefix = get_settings('prefix', 'name')
    image_type = project.image.split(prefix + "-notebook-")[1]
    password = request.POST['password']

    try:
        dashboard_server = Dashboard_server.objects.get(type = image_type)
        creator = HubUser.objects.get(username = request.user.username)
        report = Report()
        report.init(
          dashboard_server = dashboard_server,
          project = project,
          creator = creator,
          description = description,
          file = ipynb_file,
          type = type,
          password = password
        )
        report.deploy(other_files)
        report.scope = request.POST['scope']
        report.save()
        if len(request.POST['reports2remove']):
            reports2remove = request.POST['reports2remove'].split(',') if ',' in request.POST['reports2remove'] else [ request.POST['reports2remove'] ]
            for reportid in reports2remove:
                report = Report.objects.get(id = reportid, creator = creator)
                report.delete()

        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    except Exception as e:
        raise
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
        prefix = get_settings('prefix', 'name')
        dashboard_container_name = prefix + "-dashboards-" + i.name.split(prefix + "-notebook-")[1]
        docker_container = d.get_container(dashboard_container_name, original=True)
        #container, docker_container = d.get_container(dashboard_container_name)
        if docker_container:
            D = Dashboard_server()
            D.init(d, docker_container)
            D.save()

    g = Gitlab()
    for p in Project.objects.all():
         m = g.get_project_members(p.id)
         for member in m:
            hubuser = HubUser.objects.get(gitlab_id = member['id'])
            if not UserProjectBinding.objects.filter(project = p, hub_user = hubuser):
                 userp = UserProjectBinding()
                 userp.set(project = p, hub_user = hubuser)
                 userp.save()

    gitlab_projects = g.get_my_projects()
    gitlab_projects = []
    for gitlab_project in gitlab_projects:
        p = Project()
        p.init(gitlab_project)
        m = g.get_project_members(p.id)
        p.save()
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def notebooks_commitform(request):
    assert isinstance(request, HttpRequest)
    project_id = request.GET['project_id']
    project = Project.objects.get(id = project_id)
    user = request.user
    repo = repository(user, project)
    try:
        git_log = repo.log()
        git_files = repo.lsfiles()
        git_changed = repo.remote_changed()
        return render(
            request,
            'app/notebooks-gitform.html',
            context_instance=RequestContext(request,
            {
                'project': project,
                'committable_dict' : git_files,
                'commits' : git_log,
                'changedremote': git_changed,
            })
        )
    except Exception as e:
        return notebooks(request, errors = [ e ])

def notebooks_commit(request):
    def mysplit(x):
        return x[1:-1].split("','") if len(x) else []
    assert isinstance(request, HttpRequest)
    if 'cancel' in request.POST.keys():
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

    project_id = request.POST['project_id']
    project = Project.objects.get(id = project_id)
    message = request.POST['message']
    modified_files = mysplit(request.POST['modified_files'])
    deleted_files = mysplit(request.POST['deleted_files'])

    try:
        repo = repository(request.user, project)
        if len(modified_files):
            repo.add(modified_files)
        if len(deleted_files):
            repo.remove(deleted_files)
        repo.commit(message)
        repo.push()
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    except Exception as e:
        return notebooks(request, errors = [ str(e) ])

def notebooks_pull(request):
    assert isinstance(request, HttpRequest)
    if 'cancel' in request.POST.keys():
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    project_id = request.POST['project_id']
    project = Project.objects.get(id = project_id)
    user = request.user
    repo = repository(user, project)
    try:
        repo.pull()
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    except Exception as e:
        return notebooks(request, errors = [ str(e) ])
    
def notebooks_revert(request):
    assert isinstance(request, HttpRequest)
    if 'cancel' in request.POST.keys():
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    project_id = request.POST['project_id']
    project = Project.objects.get(id = project_id)
    user = request.user
    repo = repository(user, project)
    commitid = request.POST['commitid']
    try:
        repo.revert(commitid)
        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
    except Exception as e:
        return notebooks(request, errors = [ str(e) ])

    
###def notebooks_mergerequestform(request):
###    assert isinstance(request, HttpRequest)
###    next_page = request.POST['next_page']
###    project_id = request.POST['project_id']
###    target_id = request.POST['target_id']
###    title = request.POST['title']
###    description = request.POST['description']
###    g = Gitlab(request)
###    message_json = g.create_mergerequest(project_id, target_id, title, description)
###    if message_json == "":
###        return HttpResponseRedirect(next_page)
###    else:
###        return render(
###            request,
###            'app/error.html',
###            context_instance=RequestContext(request,
###            {
###                    'error_title': 'Error',
###                    'error_message': message_json,
###            })
###        )
###        

### def notebooks_mergerequestlist(request):
###     assert isinstance(request, HttpRequest)
###     itemid = request.GET['itemid']
###     path_with_namespace = request.GET['path_with_namespace']
###     g = Gitlab(request)
###     mergerequests = g.list_mergerequests(itemid)
###     return render(
###         request,
###         'app/mergerequestlist.html',
###         context_instance=RequestContext(request,
###         {
###             'mergerequests': mergerequests,
###             'path_with_namespace': path_with_namespace,
###         })
###     )
### 
### def notebooks_acceptmergerequest(request):
###     assert isinstance(request, HttpRequest)
###     project_id = request.GET['project_id']
###     mergerequestid = request.GET['mergerequestid']
###     g = Gitlab(request)
###     message_json = g.accept_mergerequest(project_id, mergerequestid)
###     if message_json == "":
###         return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
###     else:
###         return render(
###             request,
###             'app/error.html',
###             context_instance=RequestContext(request,
###             {
###                     'error_title': 'Error',
###                     'error_message': message_json,
###             })
###         )
### 
### def project_fork(request):
###     assert isinstance(request, HttpRequest)
###     itemid = request.GET['itemid']
###     g = Gitlab(request)
###     message = g.fork_project(itemid)
###     #TODO gadmin get image variable
###     print_debug(message)
###     gadmin = GitlabAdmin(request)
###     forked_project_image = gadmin.get_project_variable(itemid, 'container_image')
###     forked_project = gadmin.get_project(itemid)
###     project = g.get_project_by_name(forked_project['name'])
###     g.change_variable_value(project[0]['id'], 'container_image', forked_project_image)
###     if message == "":
###         return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
###     else:
###         return render(
###             request,
###             'app/error.html',
###             context_instance=RequestContext(request,
###             {
###                     'error_title': 'Error',
###                     'error_message': message,
###             })
###         )

def usermanagementForm(request):
    users = filter(lambda x: x.username != 'gitlabadmin', User.objects.all())
    return render(
        request,
        'app/usermanagement.html',
        context_instance=RequestContext(request,
        { 'users': users,
          'user': request.user })
    )


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
            assert k in self._data.keys(), "Unknown attribute: %s" % k
            if k == 'email':
                assert '@' in v, "E-mail address should contain @" #FIXME: regular expression
            self._data[k] = v

    def create(self):

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


        try:
            gad = GitlabAdmin()
            msg = gad.create_user(self)
            if len(msg):
                ooops.append("gitcreate: %s" % msg)
            gg = gad.get_user(dj_user.username)[0]
            dj_user.gitlab_id = gg['id']
        except Exception as e:
            ooops.append("gitcreate2: %s" % e)


        home_dir = os.path.join(get_settings('volumes', 'home'), self['username'])
        ssh_dir = os.path.join(home_dir, '.ssh')
        ###################oc_dir = os.path.join(srv_dir, '_oc', self['username'])
        oc_dir = os.path.join(home_dir, 'oc')
        git_dir = os.path.join(get_settings('volumes', 'git'), self['username'])
        davfs_dir = os.path.join(home_dir, '.davfs2')

        mkdir(home_dir, uid = dj_user.uid, gid = dj_user.gid)
        mkdir(ssh_dir, uid = dj_user.uid, gid = dj_user.gid, mode = 0b111000000)
        mkdir(oc_dir, uid = dj_user.uid, gid = dj_user.gid, mode = 0b111000000)
        mkdir(git_dir, uid = dj_user.uid, gid = dj_user.gid)
        mkdir(davfs_dir, uid = dj_user.uid, gid = dj_user.gid, mode=0b111000000)

        open(os.path.join(oc_dir, ".notmounted"), "w").close()
        
        ## prepare .gitconfig
        fn_gitconfig = os.path.join(home_dir, '.gitignore')
        with open(fn_gitconfig, 'w') as f:
            f.write("""
[user]
        name = %s %s
        email = %s
[push]
        default = matching
""" % (self['firstname'], self['lastname'], self['email']))
        os.chown(fn_gitconfig, dj_user.uid, dj_user.gid)
        ##

        ## preapare davfs secret file
        davsecret_fn = os.path.join(davfs_dir, "secrets")
        with open(davsecret_fn, "w") as f:
            f.write(os.path.join(get_settings('owncloud', 'inner_url'), "remote.php/webdav/") + " %s %s" % (self['username'], self['password']))
        os.chown(davsecret_fn, dj_user.uid, dj_user.gid)
        os.chmod(davsecret_fn, 0b110000000) 

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
        try:
            l = Ldap()
            l.delete_user(dj_user)
        except Exception as e:
            ooops.append("ldap: %s" % e)
        try:
            gad = GitlabAdmin()
            gad.delete_user(self['username'])
        except Exception as e:
            ooops.append("git: %s" % e)
        dj_user.delete()
#TODO: remove appropriate directories from the filesystem
        if len(ooops):
            raise Exception(",".join(ooops))

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
            U.delete()
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

# AUTOCOMPLETE https://djangopackages.org/grids/g/auto-complete/
def project_membersForm(request):
    me = HubUser.objects.get(username = request.user.username)
    project = Project.objects.get(id = request.GET['project_id'])
    ups = UserProjectBinding.objects.filter(project = project).exclude(hub_user = me)
    current_members = [up.hub_user for up in ups ]
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
            hubuser = HubUser.objects.get(gitlab_id = gid)
            creator_user = HubUser.objects.get(username = project.creator_name)
            if request.POST['button'] == 'Add':
                g.add_project_members(project.id, gid)
                if not UserProjectBinding.objects.filter(project = project, hub_user = hubuser):
                    userp = UserProjectBinding()
                    userp.set(project = project, hub_user = hubuser) 
                    userp.save()
                OCHelper(creator_user, project).share(hubuser)
                
            elif request.POST['button'] == 'Remove':
                g.delete_project_members(project.id, gid)
                userp = UserProjectBinding.objects.get(project = project, hub_user = hubuser)
                if userp:
                     userp.delete()
                OCHelper(creator_user, project).unshare(hubuser)
#TODO shall we remove the user's git dir???
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
    pass
###    assert isinstance(request, HttpRequest)
###    try:
###        user = request.user
###        hubuser = HubUser.objects.get(username = user.username)
###        ocspawner = OCSpawner(hubuser)
###        if request.POST['button'] == 'Start':
###            pw = request.POST['password']
###            netrc_exists = request.POST['netrc_exists'] == 'True'
###            if not netrc_exists and (len(pw) == 0):
###                raise Exception("Please provide a password so the synchronization daemon can access your owncloud storage")
###
####FIXME: machine name hardcoded
###            if len(pw):
###                fn_netrc = hubuser.file_netrc_
###                netrc = """
###machine %s
###login %s
###password %s
###"""     % ('kooplex-nginx', user.username, pw)
###                with open(fn_netrc, 'w') as f:
###                    f.write(netrc)
###                os.chown(fn_netrc, hubuser.uid, hubuser.gid)
###                os.chmod(fn_netrc, 0b111000000)
###            ocspawner.start()
###        elif request.POST['button'] == 'Stop':
###            ocspawner.stop()
###        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
###    except Exception as e:
###        return render(
###            request,
###            'app/error.html',
###            context_instance=RequestContext(request,
###                                            {
###                                                'error_title': 'Error',
###                                                'error_message': str(e),
###                                            })
###        )



def addvolume(request):
    v = Volume(name = 'tesztvolume')
    resp = v.create()
    return HttpResponse(resp)

def project_settings(request):
    assert isinstance(request, HttpRequest)
    project_id = request.POST['project_id']
    project = Project.objects.get(id = project_id)
    button = request.POST['button']
    if button == 'delete':
        g = Gitlab(request)   #FIXME: why request passed???
        message_json = g.delete_project(project_id)
        if message_json:
            project.delete()
#        remove_tree(project.sharedir_)
#TODO gitdir ??

#TODO permanently delete????
 
#        for member in UserProjectBinding.objects.filter(project = project):
#            remove_tree(project.gitdir+"/.git", member.hubuser)

    elif button == 'makepublic':
        g = Gitlab(request)
        level='public'
        g.set_project_visibility(project_id, level)
        project.visibility=level
        project.save()
    elif button == 'makeprivate':
        g = Gitlab(request)
        level = 'private'
        g.set_project_visibility(project_id, level)
        project.visibility = level
        project.save()

    elif button == 'apply':
        for k, v in request.POST.items():
            if k.startswith('project_image-'):
                project.image = v
                project.save()
        # parse shares and volumes
        mp2add, mprw, vols2add = parse_shares_and_volumes(request) #NOTE: mprw is now not rendered until nfs4 acls are working
        # update volumes if necessary
        for vpb in VolumeProjectBinding.objects.filter(project = project):
            if vpb.volume in vols2add:
                vols2add.remove(vpb.volume)
            else:
                vpb.delete()
        for vol in vols2add:
            vpb = VolumeProjectBinding(project = project, volume = vol)
            vpb.save()
        # update shares if necessary
        for mpb in MountPointProjectBinding.objects.filter(project = project):
            if mpb.mountpoint.id in mp2add:
                mp2add.remove(mpb.mountpoint.id)
            else:
                mpb.delete()
        for mpid in mp2add:
            mpb = MountPointProjectBinding(project = project, mountpoint = MountPoints.objects.get(id = mpid), readwrite = 'ro') #FIXME: hardcoded
            mpb.save()

    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

def update_bio(request):
    assert isinstance(request, HttpRequest)
    me = request.user
    location = request.POST['location'].strip()
    bio = request.POST['bio'].strip()
    user = HubUser.objects.get(username = me.username)
    user.location = location
    user.bio = bio
    user.save()
    return HttpResponseRedirect(HUB_NOTEBOOKS_URL)

urlpatterns = [
    url(r'^$', notebooks, name='notebooks'),
    url(r'^new$', project_new, name='project-new'),
    url(r'^delete_container$', container_delete, name= 'container-delete'),
    url(r'^start_container$', container_start, name = 'container-start'),
    url(r'^open_container$', container_open, name = 'container-open'),
    url(r'^clone$', notebooks_clone, name = 'notebooks-clone'),
    url(r'^preparetopublish$', notebooks_publishform, name = 'notebooks-publishform'),
    url(r'^publish$', notebooks_publish, name = 'notebooks-publish'),
    url(r'^commitform$', notebooks_commitform, name='notebooks-commitform'),
    url(r'^commit$', notebooks_commit, name='notebooks-commit'),
    url(r'^pull$', notebooks_pull, name='notebooks-pull'),
    url(r'^revert$', notebooks_revert, name='notebooks-revert'),
###    url(r'^mergerequestform$', notebooks_mergerequestform, name='notebooks-mergerequestform'),
###    url(r'^mergerequestlist', notebooks_mergerequestlist, name='notebooks-mergerequestlist'),
###    url(r'^acceptmergerequest', notebooks_acceptmergerequest, name='notebooks-acceptmergerequest'),
###    url(r'^fork$', project_fork, name='project-fork'),
    url(r'^refresh$', Refresh_database, name='refresh-db'),


    url(r'^usermanagement$', usermanagementForm, name='usermanagement-form'),
    url(r'^adduser$', usermanagement, name='usermanagement-add'),
    url(r'^deleteuser$', usermanagement2, name='usermanagement-delete'),

    url(r'^projectmembersform', project_membersForm, name='project-members-form'),
    url(r'^projectmembersmodify', project_members_modify, name='project-members-modify'),

    url(r'^oc$', toggle_oc, name='oc'),

    url(r'^addvolume$', addvolume, name='addvolume'),

    
    url(r'^project_settings$', project_settings, name='project-settings'),

    url(r'^updatebio$', update_bio, name='update-bio'),
]
