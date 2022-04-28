import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.contrib.auth.models import User

from django_tables2 import RequestConfig

from .forms import FormProject, TableShowhideProject, TableJoinProject, TableCollaborator, TableProjectContainer, TableContainer
from .models import Project, UserProjectBinding, ProjectContainerBinding
from container.models import Container

logger = logging.getLogger(__name__)

@login_required
def new(request):
    logger.debug("user %s" % request.user)
    user_id = request.POST.get('user_id')
    try:
        assert user_id is not None and int(user_id) == request.user.id, f'user id mismatch {request.user}: {request.user_id} =/= {user_id}'
        form = FormProject(request.POST, user = request.user)
        if form.is_valid():
            logger.info(form.cleaned_data)
            projectname = form.cleaned_data['name'].strip()
            subpath = form.cleaned_data['subpath'].strip()
            assert len(Project.objects.filter(subpath = subpath)) == 0, f'Project folder {subpath} is not unique'
            assert len(UserProjectBinding.objects.filter(user = request.user, project__name = projectname)) == 0, f'Project name {projectname} is not unique'
            assert len(form.cleaned_data['environments']) > 0 or form.cleaned_data['image'], "either select an image or select some environments"
            
            if subpath:
                project = Project.objects.create(name = projectname, subpath = subpath, description = form.cleaned_data['description'], scope = form.cleaned_data['scope'])
            else:
                project = Project.objects.create(name = projectname, description = form.cleaned_data['description'], scope = form.cleaned_data['scope'])
            UserProjectBinding.objects.create(user = request.user, project = project, role = UserProjectBinding.RL_CREATOR)
            messages.info(request, f'New {project}')
            if len(form.cleaned_data['environments']) > 0:
                for svc in form.cleaned_data['environments']:
                    ProjectContainerBinding.objects.create(project = project, container = svc)
                    if svc.mark_restart(f'project {project.name} added'):
                        messages.warning(request, f'Project {project.name} is added to running svc {svc.name}, which requires a restart to apply changes')
                    else:
                        messages.info(request, f'Project {project.name} is added to svc {svc.name}')
            else:
                image = form.cleaned_data['image']
                svc = Container.objects.create(name = f"{request.user.username}-{project.subpath}", user = request.user, image = image)
                ProjectContainerBinding.objects.create(project = project, container = svc)
                messages.info(request, f'New service {svc.name} is created with image {svc.image.name}')
        else:
            messages.error(request, form.errors)
        return redirect('project:list')
    except AssertionError as e:
        messages.error(request, f'Creation of project is refused: {e}')
        return redirect('project:list')
    except Exception as e:
        logger.error(f'New project not created -- {e}')
        messages.error(request, 'Creation of a new project is refused.')
        return redirect('indexpage')


@login_required
def delete_or_leave(request, project_id):
    """Delete or leave a project."""
    user = request.user
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(project_id = project_id, user = user)
        upb = UserProjectBinding.objects.get(user = user, project = project)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect('project:list')
    if upb.role == upb.RL_CREATOR:
        collab = []
        for upb_i in UserProjectBinding.objects.filter(project = project):
            if upb != upb_i:
                collab.append(upb_i.user)
                upb_i.delete()
        try:
            upb.delete()
            project.delete()
            if len(collab):
                messages.info(request, 'Users removed from collaboration: {}'.format(', '.join([  f'{u.first_name} {u.last_name} ({u.username})' for u in collab ])))
            messages.info(request, 'Project %s is deleted' % (project))
        except Exception as e:
            messages.error(request, f'Cannot delete project {project.name}. Ask the administrator to solve this error {e}')
    else:
        upb.delete()
        messages.info(request, 'You left project %s' % (project))
    return redirect('project:list')


@login_required
def layout_flip(request):
    profile = request.user.profile
    profile.layout_project_list ^= True
    profile.save()
    return redirect('project:list')


class UserProjectBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'project_list.html'
    context_object_name = 'userprojectbindinglist'

    def get_queryset(self):
        user = self.request.user
        profile = user.profile
        pattern = self.request.GET.get('project', profile.search_project_list)
        if pattern:
            projectbindings = UserProjectBinding.objects.filter(user = user, project__name__icontains = pattern).order_by('project__name')
        else:
            projectbindings = UserProjectBinding.objects.filter(user = user, is_hidden = False).order_by('project__name')
        if len(projectbindings) and pattern != profile.search_project_list:
            profile.search_project_list = pattern
            profile.save()
        return projectbindings


@login_required
def show(request, project_id):
    """Unhide project from the list."""
    logger.debug("project id %s, user %s" % (project_id, request.user))
    try:
        b = UserProjectBinding.objects.get(project__id = project_id, user = request.user, is_hidden = True)
        b.is_hidden = False
        b.save()
    except UserProjectBinding.DoesNotExist:
        messages.error(request, 'You cannot unhide the requested project.')
    return redirect('project:list')


@login_required
def hide(request, project_id):
    """Hide project from the list."""
    logger.debug("project id %s, user %s" % (project_id, request.user))
    try:
        b = UserProjectBinding.objects.get(project__id = project_id, user = request.user, is_hidden = False)
        b.is_hidden = True
        b.save()
    except UserProjectBinding.DoesNotExist:
        messages.error(request, 'You cannot hide the requested project.')
    return redirect('project:list')


def show_hide(request):
    user = request.user
    profile = user.profile
    pattern = request.POST.get('project', profile.search_project_showhide)
    if pattern:
        userprojectbindings = UserProjectBinding.objects.filter(user = user, project__name__icontains = pattern)
    else:
        userprojectbindings = UserProjectBinding.objects.filter(user = user)
    if len(userprojectbindings) and pattern != profile.search_project_showhide:
        profile.search_project_showhide = pattern
        profile.save()
    if request.POST.get('button', '') == 'apply':
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
         return redirect('project:list')

    table = TableShowhideProject(userprojectbindings)
    RequestConfig(request).configure(table)
    return render(request, 'project_showhide.html', context = { 't_project': table })


@login_required
def join(request):
    logger.debug("user %s" % request.user)
    user = request.user
    profile = user.profile
    pattern = request.POST.get('project_or_creator', profile.search_project_join)
    if request.POST.get('button', '') == 'apply':
        joined = []
        svcs = []
        for project_id in request.POST.getlist('project_ids'):
            try:
                project = Project.objects.get(id = project_id, scope__in = [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ])
                UserProjectBinding.objects.create(user = user, project = project, role = UserProjectBinding.RL_COLLABORATOR)
                joined.append(project)
                logger.info("%s joined project %s as a member" % (user, project))
                for image_id in request.POST.getlist(f'image_ids_{project_id}'):
                    i = Image.objects.get(id = image_id)
                    svc = Container.objects.create(user = user, image = i, name = f'{user.username}-{project.subpath}')
                    psb = ProjectContainerBinding.objects.create(project = project, container = svc)
                    logger.info(f'created service {svc} and binding {psb}')
                    svcs.append(svc)
            except Exception as e:
                logger.warning("%s cannot join project id %s -- %s" % (user, project_id, e))
                messages.error(request, 'You cannot join project')
        if len(joined):
            messages.info(request, 'Joined projects: {}'.format(', '.join([ p.name for p in joined ])))
        if len(svcs):
            messages.info(request, 'Created services: {}'.format(', '.join([ s.name for s in svcs ])))
        return redirect('project:list')

    joinable_bindings = UserProjectBinding.objects.filter(project__scope__in = [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ], role = UserProjectBinding.RL_CREATOR).exclude(user = user)
    joined_projects = [ upb.project for upb in UserProjectBinding.objects.filter(user = user, role__in = [ UserProjectBinding.RL_ADMIN, UserProjectBinding.RL_COLLABORATOR ]) ]
    joinable_bindings = joinable_bindings.exclude(Q(project__in = joined_projects))
    if pattern:
        joinable_bindings = joinable_bindings.filter(Q(project__name__icontains = pattern) | Q(user__first_name__icontains = pattern) | Q(user__last_name__icontains = pattern) | Q(user__username__icontains = pattern))
    if len(joinable_bindings) and pattern != profile.search_project_join:
        profile.search_project_join = pattern
        profile.save()
    table = TableJoinProject(joinable_bindings)
    RequestConfig(request).configure(table)
    return render(request, 'project_join.html', context = { 't_joinable': table })



@login_required
def configure(request, project_id):
    user = request.user
    profile = user.profile
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))

    if request.POST.get('button', '') == 'cancel':
        return redirect('project:list')
    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
    except Project.DoesNotExist as e:
        logger.error('abuse by %s project id: %s -- %s' % (user, project_id, e))
        messages.error(request, 'Project does not exist')
        return redirect('project:list')

    if request.POST.get('button', '') == 'apply':

        # meta
        project.scope = request.POST['project_scope']
        project.description = request.POST.get('description')
        project.save()

        # collaboration
        assert project.is_admin(user), "You don't have the necessary rights"
        collaborator_ids_before = set(request.POST.getlist('collaborator_ids_before'))
        collaborator_ids_after = set(request.POST.getlist('collaborator_ids_after'))
        admin_ids_before = set(request.POST.getlist('admin_ids_before'))
        admin_ids_after = set(request.POST.getlist('admin_ids_after'))
        # removal
        removed = []
        collaborator_ids_to_remove = collaborator_ids_before.difference(collaborator_ids_after)
        for i in collaborator_ids_to_remove:
            b = UserProjectBinding.objects.get(user__id = i, project = project)
            removed.append(b.user.username)
            b.delete()
        # addition
        added = []
        service_ids = request.POST.getlist('service_ids')
        collaborator_ids_to_add = collaborator_ids_after.difference(collaborator_ids_before)
        for i in collaborator_ids_to_add:
            collaborator = User.objects.get(id = i)
            if i in admin_ids_after:
                b = UserProjectBinding.objects.create(user = collaborator, project = project, role = UserProjectBinding.RL_ADMIN)
            else:
                b = UserProjectBinding.objects.create(user = collaborator, project = project, role = UserProjectBinding.RL_COLLABORATOR)
            added.append(b.user.username)
            # copy service information
            for sid in service_ids:
                svc = ProjectContainerBinding.objects.get(id = sid, container__user = user).container
                svc_copy = Container.objects.create(user = collaborator, image = svc.image, name = f'{b.user.username}-{project.subpath}')
                ProjectContainerBinding.objects.create(container = svc_copy, project = project)
                #TODO: handle volumes
        # role change
        changed = []
        collaborator_ids_to_admin = admin_ids_after.difference(admin_ids_before).intersection(collaborator_ids_after).difference(collaborator_ids_to_add)
        collaborator_ids_to_revokeadmin = admin_ids_before.difference(admin_ids_after).intersection(collaborator_ids_after).difference(collaborator_ids_to_add)
        for i in collaborator_ids_to_admin:
            b = UserProjectBinding.objects.filter(user__id = i, project = project).exclude(role = UserProjectBinding.RL_CREATOR)
            assert len(b) == 1
            b = b[0]
            b.role = UserProjectBinding.RL_ADMIN
            changed.append(b.user.username)
            b.save()
        for i in collaborator_ids_to_revokeadmin:
            b = UserProjectBinding.objects.filter(user__id = i, project = project).exclude(role = UserProjectBinding.RL_CREATOR)
            assert len(b) == 1
            b = b[0]
            b.role = UserProjectBinding.RL_COLLABORATOR
            changed.append(b.user.username)
            b.save()
        if added:
            messages.info(request, 'Added {} as colaborators'.format(', '.join(added)))
        if removed:
            messages.info(request, 'Removed {} from colaboration'.format(', '.join(removed)))
        if changed:
            messages.info(request, 'Changed collaboration roles of {}'.format(', '.join(changed)))

        # service
        psb_ids_before = set(request.POST.getlist('psb_ids_before'))
        psb_ids_after = set(request.POST.getlist('psb_ids_after'))
        # removal
        removed = []
        restart = []
        psb_ids_to_remove = psb_ids_before.difference(psb_ids_after)
        for i in psb_ids_to_remove:
            b = ProjectContainerBinding.objects.get(id = i, project = project, container__user = user)
            svc = b.container
            removed.append(svc.name)
            if svc.mark_restart(f'project {project.name} removed'):
                restart.append(svc.name)
            b.delete()
        # addition
        added = []
        svc_ids = request.POST.getlist('svc_ids')
        for i in svc_ids:
            svc = Container.objects.get(id = i, user = user)
            ProjectContainerBinding.objects.create(container = svc, project = project)
            added.append(svc.name)
            if svc.mark_restart(f'project {project.name} added'):
                restart.append(svc.name)
        if added:
            messages.info(request, 'Added service environments {0} to project {1}'.format(', '.join(added), project.name))
        if removed:
            messages.info(request, 'Removed service environments {0} from project {1}'.format(', '.join(removed), project.name))
        if restart:
            messages.warning(request, 'Restart service environments {} because they became inconsistent'.format(', '.join(restart)))

        return redirect('project:list')
    else:
        active_tab = request.GET.get('active_tab', 'collaboration')

        pattern = request.GET.get('pattern', profile.search_project_collaborator) if active_tab == 'collaboration' else profile.search_project_collaborator
        if pattern:
            everybodyelse = user.profile.everybodyelse_like(pattern)
        else:
            everybodyelse = user.profile.everybodyelse
        if len(everybodyelse) and pattern != profile.search_project_collaborator:
            profile.search_project_collaborator = pattern
            profile.save()
        table_collaborator = TableCollaborator(project, everybodyelse)
        RequestConfig(request).configure(table_collaborator)

        table_project_container = TableProjectContainer(ProjectContainerBinding.objects.filter(container__user = user, project = project))
        RequestConfig(request).configure(table_project_container)

        pattern = request.GET.get('pattern', profile.search_project_container) if active_tab == 'service' else profile.search_project_container
        if pattern:
            containers = Container.objects.filter(user = user, name__icontains = pattern)
        else:
            containers = Container.objects.filter(user = user)
        if len(containers) and pattern != profile.search_project_container:
            profile.search_project_container = pattern
            profile.save()
        table_container = TableContainer(UserProjectBinding.objects.get(user = user, project = project), containers)
        RequestConfig(request).configure(table_container)

        context_dict = {
            'project': project,
            'active': active_tab,
            't_collaborators': table_collaborator,
            't_services': table_project_container,
            't_all_services': table_container,
        }
        return render(request, 'project_configure.html', context = context_dict)


