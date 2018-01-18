import re

from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest
from django.template import RequestContext
import logging
logger = logging.getLogger(__name__)

from kooplex.hub.models import *
from kooplex.lib import spawn_project_container, stop_project_container
from kooplex.lib import gitlab_create_project


def projects(request, *v, **kw):
    """Renders the projectlist page."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        logger.debug('User not authenticated yet --> goes to login page')
        return redirect('login')
    logger.debug('User authenticated %s' %request.user)
    logger.info('Userauthenticated')

    PUBLIC = ScopeType.objects.get(name = 'public')
    NOTEBOOK = ContainerType.objects.get(name = 'notebook')
    user = request.user
    projects_mine = Project.objects.filter(owner = user)
    projects_sharedwithme = sorted([ upb.project for upb in UserProjectBinding.objects.filter(user = user) ])
    projects_public = sorted(Project.objects.filter(scope = PUBLIC).exclude(owner = user))
    running = [ c.project for c in Container.objects.filter(user = user, is_running = True, container_type = NOTEBOOK) ]
    users = sorted(User.objects.all())
    images = Image.objects.all()
    scopes = ScopeType.objects.all()
    volumes = Volume.objects.all()
    logger.debug('Rendering projects.html')

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
            'users': users,
            'images' : images,
            'scopes' : scopes,
            'volumes': volumes,
            'errors' : kw.get('errors', None),
            'year' : 2018,
        })
    )


def project_new(request):
    """Handles the creation of a new project."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')

    user = request.user
    name = request.POST['project_name'].strip()
    description = request.POST['project_description'].strip()
    scope = request.POST['button']
    template = request.POST.get('project_template')
    #FIXME: parse shares and volumes
    logger.debug('New project to be created: %s'%name)

    errors = []
    if not re.match(r'^[a-zA-Z][0-9a-zA-Z_-]*$', name):
        errors.append('For project name specification please use only Upper/lower case letters, hyphens and underscores.')
    if not re.match(r'^[0-9a-zA-Z_ -]*$', description):
        errors.append('In your project description use only Upper/lower case letters, hyphens, spaces and underscores.')
    if len(errors):
        return projects(request, kw = { 'errors': errors })
        
    if template.startswith('clonable_project='):
        pass
#FIXME:
#        name, owner = template.split('=')[-1].split('@')
#        project = Project.objects.get(name = name, owner_username = owner)
#        project_image_name = project.image
#        # Retrieve former_shares and unify with users current choices
#        for mpb in MountPointProjectBinding.objects.filter(project = project):
#            mp.append(mpb.id)
#        mp = list(set(mp))
#        # Retrieve former_volumes and unify with users current choices
#        for vpb in VolumeProjectBinding.objects.filter(project = project):
#            vols.append(vpb.volume)
#        vols = list(set(vols))
#        cloned_project = True
    elif template.startswith('image='):
        imagename = template.split('=')[-1]
        logger.debug('Project to be created from image: %s' % imagename)
        cloned_project = False
#    debug_logger.debug("Create project %s - GitLab"% project_name)
    scope = ScopeType.objects.get(name = scope)
    image = Image.objects.get(name = imagename)
    project = Project(name = name, owner = user, description = description, image = image, scope = scope)
    gitlab_create_project(project, request) #FIXME: why we give request?
    logger.debug('New project created in GitLab: %s' % name)
    project.save()
    logger.debug('New project saved in HubDB: %s' % name)
    return redirect('projects')
#FIXME:
#####        #Add image_name to project
#####        # manage shares
#####        while len(mp):
#####            mpid = mp.pop()
#####            mpb = MountPointProjectBinding()
#####            mpb.project = p
#####            mpb.mountpoint = MountPoints.objects.get(id = mpid)
#####            mpb.readwrite = mpid in mprw
#####            mpb.save()
#####
#####        # manage volumes
#####        while len(vols):
#####            vol = vols.pop()
#####            vpb = VolumeProjectBinding(volume = vol, project = p)
#####            vpb.save()
#####
#####        OCHelper(hubuser, p).mkdir()
#####
#####        if cloned_project:
###### Create a magic script to clone ancient projects content
#####            ancientprojecturl = "ssh://git@%s/%s.git" % (get_settings('gitlab', 'ssh_host'), project.path_with_namespace)
#####            commitmsg = "Snapshot commit of project %s" % project
#####            script = """#! /bin/bash
#####TMPFOLDER=$(mktemp -d)
#####git clone %(url)s ${TMPFOLDER}
#####cd ${TMPFOLDER}
#####rm -rf ./.git/
#####mv * ~/git/
#####for hidden in $(echo .?* | sed s/'\.\.'//) ; do
#####  mv $hidden ~/git
#####done
#####cd ~/git
#####git add --all
#####git commit -a -m "%(message)s"
#####git push origin master
#####rm -rf ${TMPFOLDER}
#####rm ~/$(basename $0)
#####            """ % { 'url': ancientprojecturl, 'message': commitmsg }
#####            home_dir = os.path.join(get_settings('volumes', 'home'), p.owner_username)
#####            fn_basename = ".gitclone-%s.sh" % p.name
#####            fn_script = os.path.join(home_dir, fn_basename)
#####            open(fn_script, 'w').write(script)
#####            os.chmod(fn_script, 0b111000000)
#####            hubuser = HubUser.objects.get(username = p.owner_username)
#####            os.chown(fn_script, int(hubuser.uid), int(hubuser.gid))
#####        else:
###### Create a README file
#####            g.create_project_readme(p.id, "README.md", "* proba", "Created a default README")
#####        return HttpResponseRedirect(HUB_NOTEBOOKS_URL)
#####    except Exception as e:
#####        return render(
#####            request,
#####            'app/error.html',
#####            context_instance=RequestContext(request,
#####                                            {
#####                                                'error_title': 'Error',
#####                                                'error_message': str(e),
#####                                            })
#####        )


def project_configure(request):
    """Handles the project configuration."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:


def project_collaborate(request):
    """Handles the project user collaborations."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:


def project_start(request):
    """Starts. the project container."""
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
    """Opens the project container."""
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
    return redirect(container.url_with_token)


def project_stop(request):
    """Stops project and delete container."""
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

def project_versioning(request):
    """Handles the git."""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect('login')
#FIXME:




urlpatterns = [
    url(r'^/?$', projects, name = 'projects'),
    url(r'^/new$', project_new, name = 'project-new'), 
    url(r'^/configure$', project_configure, name = 'project-settings'), 
    url(r'^/collaborate$', project_collaborate, name = 'project-members-form'), 
    url(r'^/versioncontrol$', project_versioning, name = 'project-commit'), 
    url(r'^/start$', project_start, name = 'container-start'), 
    url(r'^/open$', project_open, name = 'container-open'), 
    url(r'^/stop$', project_stop, name = 'container-delete'), 
]

