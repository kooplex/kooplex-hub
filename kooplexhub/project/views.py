import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views import generic
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.contrib.auth.models import User
#from django.urls import reverse

from .forms import FormProject, FormProjectWithContainer
from .forms import TableShowhideProject, TableJoinProject, TableCollaborator, TableContainer
from .models import Project, UserProjectBinding, ProjectContainerBinding
from container.models import Container

logger = logging.getLogger(__name__)


class NewProjectView(LoginRequiredMixin, generic.FormView):
    template_name = 'project_new.html'
    form_class = FormProjectWithContainer
    success_url = '/hub/project/list/' #FIXME: django.urls.reverse or shortcuts.reverse does not work reverse('project:list')

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['environments'] = Container.objects.filter(user = user)
        initial['projectid'] = None
        initial['userid'] = user.id
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_project'] = True
        context['submenu'] = 'new'
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        projectname = form.cleaned_data['name'].strip()
        subpath = form.cleaned_data['subpath'].strip()
        user = self.request.user
        if subpath:
            project = Project.objects.create(name = projectname, subpath = subpath, description = form.cleaned_data['description'], scope = form.cleaned_data['scope'])
        else:
            project = Project.objects.create(name = projectname, description = form.cleaned_data['description'], scope = form.cleaned_data['scope'])
        UserProjectBinding.objects.create(user = user, project = project, role = UserProjectBinding.RL_CREATOR)
        messages.info(self.request, f'New project created {project}')
        if len(form.cleaned_data['environments']) > 0:
            for container in form.cleaned_data['environments']:
                ProjectContainerBinding.objects.create(project = project, container = container)
                if container.mark_restart(f'project {project.name} added'):
                    messages.warning(self.request, f'Project {project.name} is added to running environment {container.name}, which requires a restart to apply changes')
                else:
                    messages.info(self.request, f'Project {project.name} is added to environment {container.name}')
        else:
            image = form.cleaned_data['image']
            container = Container.objects.create(name = f"{user.username}-{project.subpath}", friendly_name = project.subpath, user = user, image = image)
            ProjectContainerBinding.objects.create(project = project, container = container)
            messages.info(self.request, f'New service {container.name} is created with image {container.image.name}')
        return super().form_valid(form)


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


class UserProjectBindingListView(LoginRequiredMixin, generic.ListView):
    template_name = 'project_list.html'
    context_object_name = 'userprojectbindinglist'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submenu'] = 'list'
        context['menu_project'] = True
        return context

    def get_queryset(self):
        user = self.request.user
        projectbindings = UserProjectBinding.objects.filter(user = user, is_hidden = False).order_by('project__name')
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
    userprojectbindings = UserProjectBinding.objects.filter(user = user)
    if request.POST.get('button', '') == 'apply':
        show_ids = list(map(int, request.POST.getlist('show')))
        n_hide = 0
        n_unhide = 0
        for upb in userprojectbindings:
            if upb.is_hidden and upb.id in show_ids:
                upb.is_hidden = False
                upb.save()
                n_unhide += 1
            elif not upb.is_hidden and not upb.id in show_ids:
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

    table = TableShowhideProject(userprojectbindings, user = user)
    return render(request, 'project_showhide.html', context = { 't_project': table, 'menu_project': True, 'submenu': 'showhide' })


@login_required
def join(request):
    logger.debug("user %s" % request.user)
    user = request.user
    profile = user.profile
    if request.POST.get('button', '') == 'apply':
        joined = []
        containers = []
        for project_id in request.POST.getlist('project_ids'):
            try:
                project = Project.objects.get(id = project_id, scope__in = [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ])
                UserProjectBinding.objects.create(user = user, project = project, role = UserProjectBinding.RL_COLLABORATOR)
                joined.append(project)
                logger.info("%s joined project %s as a member" % (user, project))
                for image_id in request.POST.getlist(f'image_ids_{project_id}'):
                    i = Image.objects.get(id = image_id)
                    container = Container.objects.create(user = user, image = i, name = f'{user.username}-{project.subpath}')
                    psb = ProjectContainerBinding.objects.create(project = project, container = container)
                    logger.info(f'created service {container} and binding {psb}')
                    containers.append(container)
            except Exception as e:
                logger.warning("%s cannot join project id %s -- %s" % (user, project_id, e))
                messages.error(request, 'You cannot join project')
        if len(joined):
            messages.info(request, 'Joined projects: {}'.format(', '.join([ p.name for p in joined ])))
        if len(containers):
            messages.info(request, 'Created services: {}'.format(', '.join([ s.name for s in containers ])))
        return redirect('project:list')

    joinable_bindings = UserProjectBinding.objects.filter(project__scope__in = [ Project.SCP_INTERNAL, Project.SCP_PUBLIC ], role = UserProjectBinding.RL_CREATOR).exclude(user = user)
    joined_projects = [ upb.project for upb in UserProjectBinding.objects.filter(user = user, role__in = [ UserProjectBinding.RL_ADMIN, UserProjectBinding.RL_COLLABORATOR ]) ]
    joinable_bindings = joinable_bindings.exclude(Q(project__in = joined_projects))
    table = TableJoinProject(joinable_bindings)
    return render(request, 'project_join.html', context = { 't_joinable': table, 'menu_project': True, 'submenu': 'join' })


@login_required
def configure(request, project_id):
    user = request.user
    profile = user.profile
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))

    try:
        project = Project.get_userproject(project_id = project_id, user = request.user)
    except Project.DoesNotExist as e:
        logger.error('abuse by %s project id: %s -- %s' % (user, project_id, e))
        messages.error(request, 'Project does not exist')
        return redirect('project:list')

    context_dict = {
        'menu_project': True,
        'active': request.COOKIES.get('configure_project_tab', 'collaboration'),
        'form': FormProject(user = user, project = project),
        'project': project,
        't_users': TableCollaborator(project, user, collaborator_table = False),
        't_collaborators': TableCollaborator(project, user, collaborator_table = True),
        't_services': TableContainer(user = user, project = project, axis = 'project'),
        't_all_services': TableContainer(user = user, project = project, axis = 'user')
    }

    return render(request, 'project_configure.html', context = context_dict)


@login_required
def configure_save(request):
    if request.POST.get('button', '') == 'cancel':
        return redirect('project:list')
    user = request.user
    project_id = request.POST.get('projectid')
    try:
        project = Project.get_userproject(project_id = project_id, user = user)
    except Project.DoesNotExist as e:
        logger.error(f'abuse by {user} project id: {project_id} -- {e}')
        messages.error(request, 'Project does not exist')
        return redirect('project:list')
    # meta
    form = FormProject(request.POST)
    if form.is_valid():
        project.name = form.cleaned_data['name']
        project.scope = form.cleaned_data['scope']
        project.description = form.cleaned_data['description']
        project.save()

    # collaboration
    if not project.is_admin(user):
        logger.error(f'abuse by {user} modify project {project} collaboration')
        messages.error(request, "You don't have the necessary rights")
        return redirect('project:list')
    added = []
    for uid in request.POST.getlist('user_id'):
        collaborator = User.objects.get(id = uid)
        UserProjectBinding.objects.create(user = collaborator, project = project, role = UserProjectBinding.RL_COLLABORATOR) #FIXME: roles
        added.append(f"{collaborator.first_name} {collaborator.last_name}")
    if added:
        messages.info(request, 'Added {} as colaborators to project {}.'.format(', '.join(added), project.name))
    removed = []
    for bid in request.POST.getlist('_userprojectbinding_id'):
        b = UserProjectBinding.objects.get(id = bid, project = project)
        b.delete()
        collaborator = b.user
        removed.append(f"{collaborator.first_name} {collaborator.last_name}")
    if removed:
        messages.info(request, 'Removed {} from project {} collaborations.'.format(', '.join(removed), project.name))

    # service
    cids_before = { b.container.id: b for b in ProjectContainerBinding.objects.filter(project = project, container__user = user) }
    cids_after = request.POST.getlist('attach')
    detached = []
    cids_to_remove = set(cids_before.keys()).difference(cids_after)
    for i in cids_to_remove:
         b = cids_before[i]
         container = b.container
         detached.append(container.name)
         container.mark_restart(f'project {project.name} removed')
         b.delete()
    if detached:
        messages.info(request, 'Project {} removed from containers {}.'.format(project.name, ', '.join(detached)))
    attached = []
    cids_to_add = set(cids_after).difference(cids_before.keys())
    for i in cids_to_add:
        container = Container.objects.get(id = i, user = user)
        b = ProjectContainerBinding.objects.create(container = container, project = project)
        attached.append(container.name)
        container.mark_restart(f'project {project.name} added')
    if attached:
        messages.info(request, 'Project {} added to containers {}.'.format(project.name, ', '.join(attached)))

    return redirect('project:list')

