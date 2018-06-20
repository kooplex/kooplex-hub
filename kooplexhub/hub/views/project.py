import logging

from django.contrib import messages
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from hub.models import Project, UserProjectBinding, Volume
from hub.models import Image

from kooplex.logic import configure_project

logger = logging.getLogger(__name__)

#
#FIXME: POST only
@login_required
def configure(request):
    """Handles the project configuration."""
    logger.debug("user %s" % request.user)
    button = request.POST.get('button')
    project_id = request.POST.get('project_id')
    next_page = request.POST.get('next_page', 'teaching:list') #FIXME
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect(next_page)
#    if button == 'delete':
#        if project.owner == request.user:
#            delete_project(project)
#        else:
#            messages.error(request, 'Project %s is not yours' % project)
#            return redirect('projects')
#    elif button == 'quit':
#        if project.owner == request.user:
#            messages.error(request, 'You are the owner of the project %s, you cannot leave it' % project)
#            return redirect('projects')
#        else:
#            leave_project(project, request.user)
#    elif button == 'apply':
    if button == 'apply':
#        collaborators = [ User.objects.get(id = x) for x in request.POST.getlist('collaborators') ]
        volumes_fun = [ Volume.objects.get(id = x) for x in request.POST.getlist('func_volumes') ]
        volumes_stg = [ Volume.objects.get(id = x) for x in request.POST.getlist('stg_volumes') ]
        image = Image.objects.get(name = request.POST['project_image'])
#        scope = ScopeType.objects.get(name = request.POST['project_scope'])
        ##marked_to_remove = configure_project(project, image, scope, volumes, collaborators)
        description = request.POST.get('course_description')
        marked_to_remove = configure_project(project, image = image, volumes_functional = volumes_fun, volumes_storage = volumes_stg, description=description)
        if marked_to_remove:
            messages.info(request, '%d running containers of project %s will be removed when you stop. Changes take effect after a restart.' % (marked_to_remove, project))
    return redirect(next_page)

@login_required
def manage(request):
    """Manage your projects"""
    logger.debug("user %s" % (request.user))
    next_page = request.POST.get('next_page', 'teaching:list') #FIXME
    hide_courseprojects = [ int(i) for i in request.POST.getlist('hide_courseprojects') ]
    user = request.user
    n_hide = 0
    n_unhide = 0
    n_oops = 0
    for project in user.profile.courseprojects_taught:
        if project.is_hiddenbyuser(user) and not project.id in hide_courseprojects:
            try:
                UserProjectBinding.setvisibility(project, user, hide = False)
                n_unhide += 1
            except:
                n_oops += 1
        elif not project.is_hiddenbyuser(user) and project.id in hide_courseprojects:
            try:
                UserProjectBinding.setvisibility(project, user, hide = True)
                n_hide += 1
            except:
                n_oops += 1
    msgs = []
    if n_hide:
        msgs.append('%d projects are hidden.' % n_hide)
    if n_unhide:
        msgs.append('%d projects are unhidden.' % n_unhide)
    if len(msgs):
        messages.info(request, ' '.join(msgs))
    if n_oops:
        message.error(request, "Could not set visibility in %d cases due to errors")
    return redirect(next_page)

@login_required
def hide(request, project_id):
    """Hide project from the list."""
    logger.debug("project.id = %s, user %s" % (project_id, request.user))
    next_page = request.GET.get('next_page', 'teaching:list') #FIXME
    try:
        project = Project.objects.get(id = project_id)
        UserProjectBinding.setvisibility(project, request.user, hide = True)
    except Project.DoesNotExist:
        messages.error(request, 'You cannot hide the requested project.')
    except ProjectDoesNotExist:
        messages.error(request, 'You cannot hide the requested project.')
    return redirect(next_page)

def bla(request):
    pass

urlpatterns = [
    url(r'^list/mine/?$', bla, name = 'mine'), 
    url(r'^configure/?$', configure, name = 'settings'), 
    url(r'^manage/?$', manage, name = 'manage'), 
    url(r'^hide/(?P<project_id>\d+)$', hide, name = 'hide'), 
]

