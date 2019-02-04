import logging

from django.contrib import messages
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.html import format_html
import django_tables2 as tables
from django_tables2 import RequestConfig
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from kooplex.lib import list_projects
from kooplex.lib import now

from hub.forms import FormProject
from hub.forms import table_collaboration, T_JOINABLEPROJECT
from hub.forms import table_vcproject
from hub.models import Project, UserProjectBinding, Volume
from hub.models import Image
from hub.models import Profile
from hub.models import VCToken, VCProject, VCProjectProjectBinding

logger = logging.getLogger(__name__)


@login_required
def new(request):
    logger.debug("user %s" % request.user)
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == request.user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
        projectname = request.POST.get('name')
        for upb in UserProjectBinding.objects.filter(user = request.user):
            assert upb.project.name != projectname, "Not a unique name"
        form = FormProject(request.POST)
        form.save()
        UserProjectBinding.objects.create(user = request.user, project = form.instance, role = UserProjectBinding.RL_CREATOR)
        messages.info(request, 'Your new project is created')
        return redirect('project:list')
    except Exception as e:
        logger.error("New project not created -- %s" % e)
        messages.error(request, 'Creation of a new project is refused.')
        return redirect('indexpage')
        

@login_required
def join(request):
    logger.debug("user %s" % request.user)
    user = request.user
    if request.method == 'GET':
        project_public_and_internal = set(Project.objects.filter(Q(scope = Project.SCP_INTERNAL) | Q(scope = Project.SCP_PUBLIC)))
        project_mine = set([ upb.project for upb in UserProjectBinding.objects.filter(user = user) ])
        project_joinable = project_public_and_internal.difference(project_mine)
        table_joinable = T_JOINABLEPROJECT([ UserProjectBinding.objects.get(project = p, role = UserProjectBinding.RL_CREATOR) for p in project_joinable ])
        RequestConfig(request).configure(table_joinable)
        context_dict = {
            't_joinable': table_joinable,
        }
        return render(request, 'project/join.html', context = context_dict)
    else:
        joined = []
        for project_id in request.POST.getlist('project_ids'):
            try:
                project = Project.objects.get(id = project_id)
                assert project.scope in [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ], 'Permission denied to join %s' % project
                UserProjectBinding.objects.create(user = user, project = project, role = UserProjectBinding.RL_COLLABORATOR)
                joined.append(str(project))
                logger.info("%s joined project %s as a member" % (user, project))
            except Exception as e:
                logger.warning("%s cannot join project %s -- %s" % (user, project, e))
                messages.error(request, 'You cannot join project % s' % project)
        if len(joined):
            messages.info(request, 'Joined projects: %s' % '\n'.join(joined))

        return redirect('project:list')


@login_required
def listprojects(request):
    """Renders the projectlist page for courses taught."""
    logger.debug('Rendering project.html')
    context_dict = {
        'next_page': 'project:list',
        'menu_project': 'active',
    }
    return render(request, 'project/list.html', context = context_dict)


class ProjectSelectionColumn(tables.Column):
    def render(self, record):
        state = "checked" if record.is_hidden else ""
        return format_html('<input type="checkbox" name="selection" value="%s" %s>' % (record.id, state))

class T_PROJECT(tables.Table):
    id = ProjectSelectionColumn(verbose_name = 'Hide', orderable = False)
    class Meta:
        model = UserProjectBinding
        fields = ('id', 'project')
        sequence = ('id', 'project')
        attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }

def sel_col(project):
    class VolumeSelectionColumn(tables.Column):
        def render(self, record):
            state = "checked" if record in project.volumes else ""
            return format_html('<input type="checkbox" name="selection" value="%s" %s>' % (record.id, state))
    return VolumeSelectionColumn

def sel_table(user, project, volumetype):
    if volumetype == 'functional': #FIXME: Volume.FUNCTIONAL
        user_volumes = user.profile.functional_volumes
    elif volumetype == 'storage':
        user_volumes = user.profile.storage_volumes
    column = sel_col(project)

    class T_VOLUME(tables.Table):
        id = column(verbose_name = 'Selection')
    
        class Meta:
            model = Volume
            exclude = ('name', 'volumetype')
            attrs = { "class": "table-striped table-bordered", "td": { "style": "padding:.5ex" } }
    return T_VOLUME(user_volumes)


@login_required
def conf_meta(request, project_id, next_page):
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
    except Project.DoesNotExist as e:
        logger.error('abuse by %s project id: %s -- %s' % (user, project_id, e))
        messages.error(request, 'Project does not exist')
        return redirect(next_page)

    if request.method == 'POST' and request.POST.get('button') == 'apply':
        project.scope = request.POST['project_scope']
        project.description = request.POST.get('description')
        project.save()
        return redirect(next_page)
    else:
        context_dict = {
            'project': project, 
            'submenu': 'meta',
            'next_page': next_page,
        }
        return render(request, 'project/configure.html', context = context_dict)


@login_required
def conf_collab(request, project_id, next_page):
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
        assert project.is_admin(user), "%s is not admin of %s" % (user, project)
    except Exception as e:
        logger.error('abuse by %s project id: %s -- %s' % (user, project_id, e))
        messages.error(request, 'Unauthorized request.')
        return redirect(next_page)

    sort_info = request.GET.get('sort') if request.method == 'GET' else request.POST.get('sort')
    if request.method == 'POST' and request.POST.get('button') == 'apply':
        msg = project.set_roles(request.POST.getlist('role_map'))
        if len(msg):
            messages.info(request, '\n'.join(msg))
        return redirect(next_page)
    elif (request.method == 'POST' and request.POST.get('button') == 'search') or request.method == 'GET':
        pattern = request.POST.get('name', '')
        table = table_collaboration(project)
        table_collaborators = table(user.profile.everybodyelse) if pattern == '' else table(user.profile.everybodyelse_like(pattern))
        RequestConfig(request).configure(table_collaborators)
        context_dict = {
            'project': project, 
            'can_configure': True,
            't_collaborators': table_collaborators,
            'submenu': 'collaboration',
            'next_page': next_page,
            'search_name': pattern,
            'sort': sort_info,
        }
        return render(request, 'project/configure.html', context = context_dict)


@login_required
def conf_environment(request, project_id, next_page):
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
        assert project.is_admin(user), "%s is not admin of %s" % (user, project)
    except Exception as e:
        logger.error('abuse by %s project id: %s -- %s' % (user, project_id, e))
        messages.error(request, 'Unauthorized request.')
        return redirect(next_page)

    if request.method == 'POST' and request.POST.get('button') == 'apply':
        volumes = [ Volume.objects.get(id = x) for x in request.POST.getlist('selection') ]
        project.set_volumes(volumes)
        imagename = request.POST['project_image']
        project.image = Image.objects.get(name = imagename) if imagename != 'None' else None
        project.save()
        return redirect(next_page)
    else:
        context_dict = {
            'images': Image.objects.all(),
            'project': project, 
            't_volumes_fun': sel_table(user = user, project = project, volumetype = 'functional'), #FIXME: tables placed in forms/ ReqConfig
            'submenu': 'environment',
            'next_page': next_page,
        }
        return render(request, 'project/configure.html', context = context_dict)


@login_required
def conf_voldata(request, project_id, next_page):
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
        assert project.is_admin(user), "%s is not admin of %s" % (user, project)
    except Exception as e:
        logger.error('abuse by %s project id: %s -- %s' % (user, project_id, e))
        messages.error(request, 'Unauthorized request.')
        return redirect(next_page)

    if request.method == 'POST' and request.POST.get('button') == 'apply':
        volumes = [ Volume.objects.get(id = x) for x in request.POST.getlist('selection') ]
        project.set_volumes(volumes)
        return redirect(next_page)
    else:
        context_dict = {
            'project': project, 
            't_volumes_stg': sel_table(user = user, project = project, volumetype = 'storage'),    #FIXME: like above
            'submenu': 'storage',
            'next_page': next_page,
        }
        return render(request, 'project/configure.html', context = context_dict)


@login_required
def conf_versioncontrol(request, project_id, next_page):
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
        assert project.is_admin(user), "%s is not admin of %s" % (user, project)
    except Exception as e:
        logger.error('abuse by %s project id: %s -- %s' % (user, project_id, e))
        messages.error(request, 'Unauthorized request.')
        return redirect(next_page)

    sort_info = request.GET.get('sort') if request.method == 'GET' else request.POST.get('sort')
    if request.method == 'POST' and request.POST.get('button') == 'apply':
        msgs = []
        for id_create in request.POST.getlist('vcp_ids'):
            vcp = VCProject.objects.get(id = id_create)
            if vcp.token.user != user:
                logger.error("Unauthorized request vcp: %s, user: %s" % (vcp, user))
                continue
            VCProjectProjectBinding.objects.create(project = project, vcproject = vcp)
            msgs.append('Bound %s to repotsitory %s.' % (project, vcp))
        for id_remove in set(request.POST.getlist('vcppb_ids_before')).difference(set(request.POST.getlist('vcppb_ids_after'))):
            try:
                vcppb = VCProjectProjectBinding.objects.get(id = id_remove, project = project)
                if vcppb.vcproject.token.user != user:
                    logger.error("Unauthorized request vcp: %s, user: %s" % (vcp, user))
                    continue
                msgs.append('Project %s is not bound to repository %s any more.' % (project, vcppb.vcproject))
                vcppb.delete()
            except VCProjectProjectBinding.DoesNotExist:
                logger.error("Is %s hacking" % user)
        if len(msgs):
            messages.info(request, ' '.join(msgs))
        return redirect(next_page)
    elif (request.method == 'POST' and request.POST.get('button') == 'search') or request.method == 'GET':
        t = table_vcproject(project)
        pattern = request.POST.get('repository', '')
        table_vcp = t(VCProject.f_user(user = user)) if pattern == '' else t(VCProject.f_user_namelike(user = user, l = pattern))
        RequestConfig(request).configure(table_vcp)
        context_dict = {
            'project': project, 
            't_vcp': table_vcp, 
            'submenu': 'versioncontrol',
            'next_page': next_page,
            'search_repository': pattern,
            'sort': sort_info,
        }
        return render(request, 'project/configure.html', context = context_dict)
    else:
        return redirect(next_page)


@login_required
def delete_leave(request, project_id, next_page):
    """Delete or leave a project."""
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect(next_page)
    if project.is_admin(request.user):
        project.delete()
        messages.info(request, 'Project %s is deleted' % (project))
    elif project.is_collaborator(request.user):
        UserProjectBinding.objects.get(project = project, user = request.user).delete()
        messages.info(request, 'You left project %s' % (project))
    return redirect(next_page)


@login_required
def show_hide(request, next_page):
    """Manage your projects"""
    user = request.user
    logger.debug("user %s method %s" % (user, request.method))
    userprojectbindings = user.profile.projectbindings
    #userprojectbindings_course = user.profile.courseprojects_taught_NEW() #FIXME: diak is hideolhat ?
    if request.method == 'GET':
        table_project = T_PROJECT(userprojectbindings)
        #table_course = T_PROJECT(userprojectbindings_course)
        RequestConfig(request).configure(table_project)
        #RequestConfig(request).configure(table_course)
        context_dict = {
            't_project': table_project,
            #'t_course': table_course,
            'next_page': next_page,
        }
        return render(request, 'project/manage.html', context = context_dict)
    else:
        hide_bindingids_req = set([ int(i) for i in request.POST.getlist('selection') ])
        n_hide = 0
        n_unhide = 0
        for upb in set(userprojectbindings):#.union(userprojectbindings_course):
            if upb.is_hidden and not upb.id in hide_bindingids_req:
                upb.is_hidden = False
                upb.save()
                n_unhide += 1
            elif not upb.is_hidden and upb.id in hide_bindingids_req:
                upb.is_hidden = True
                upb.save()
                n_hide += 1
        msgs = []
        if n_hide:
            msgs.append('%d projects are hidden.' % n_hide)
        if n_unhide:
            msgs.append('%d projects are unhidden.' % n_unhide)
        if len(msgs):
            messages.info(request, ' '.join(msgs))
        return redirect(next_page)

@login_required
def hide(request, project_id, next_page):
    """Hide project from the list."""
    logger.debug("project id %s, user %s" % (project_id, request.user))
    try:
        project = Project.objects.get(id = project_id)
        UserProjectBinding.setvisibility(project, request.user, hide = True)
    except Project.DoesNotExist:
        messages.error(request, 'You cannot hide the requested project.')
    except ProjectDoesNotExist:
        messages.error(request, 'You cannot hide the requested project.')
    return redirect(next_page)


@login_required
def vcrefresh(request, token_id, project_id):
    """Refresh users version control repository projects."""
    user = request.user
    logger.debug("user %s (project_id %s)" % (user, project_id))
    try:
        now_ = now()
        token = VCToken.objects.get(user = user, id = token_id)
        old_list = list(VCProject.objects.filter(token = token))
        cnt_new = 0
        cnt_del = 0
        for p_name in list_projects(token):
            try:
                p = VCProject.objects.get(token = token, project_name = p_name)
                p.last_seen = now_
                p.save()
                old_list.remove(p)
                logger.debug('still present: %s' % p_name)
            except VCProject.DoesNotExist:
                VCProject.objects.create(token = token, project_name = p_name)
                logger.debug('inserted present: %s' % p_name)
                cnt_new += 1
        while len(old_list):
            p = old_list.pop()
            p.remove()
            logger.debug('removed: %s' % p.project_name)
            cnt_del += 1
        if cnt_new:
            messages.info(request, "%d new project items found" % cnt_new)
        if cnt_del:
            messages.warning(request, "%d project items removed" % cnt_del)
        token.last_used = now_
        token.save()
    except VCToken.DoesNotExist:
        messages.error(requset, "System abuse")
    return redirect('project:conf_versioncontrol', project_id, 'project:list')


urlpatterns = [
    url(r'^list', listprojects, name = 'list'), 
    url(r'^new/?$', new, name = 'new'), 
    url(r'^join/?$', join, name = 'join'), 
    url(r'^configure/(?P<project_id>\d+)/meta/(?P<next_page>\w+:?\w*)$', conf_meta, name = 'conf_meta'), 
    url(r'^configure/(?P<project_id>\d+)/collaboration/(?P<next_page>\w+:?\w*)$', conf_collab, name = 'conf_collaboration'), 
    url(r'^configure/(?P<project_id>\d+)/environment/(?P<next_page>\w+:?\w*)$', conf_environment, name = 'conf_environment'), 
    url(r'^configure/(?P<project_id>\d+)/storage/(?P<next_page>\w+:?\w*)$', conf_voldata, name = 'conf_storage'), 
    url(r'^configure/(?P<project_id>\d+)/versioncontrol/(?P<next_page>\w+:?\w*)$', conf_versioncontrol, name = 'conf_versioncontrol'), 
    url(r'^vcrefresh/(?P<token_id>\d+)/(?P<project_id>\d+)$', vcrefresh, name = 'vcrefresh'), 
    url(r'^delete/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', delete_leave, name = 'delete'), 
    url(r'^show/(?P<next_page>\w+:?\w*)$', show_hide, name = 'showhide'),
    url(r'^hide/(?P<project_id>\d+)/(?P<next_page>\w+:?\w*)$', hide, name = 'hide'), 
]

