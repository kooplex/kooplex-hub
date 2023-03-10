import logging

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.views import generic
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.contrib.auth.models import User
#from django.urls import reverse

from .forms import FormProject, FormJoinProject
from .models import Project, UserProjectBinding, ProjectContainerBinding
from container.models import Container
from volume.models import Volume, VolumeContainerBinding

from kooplexhub.settings import KOOPLEX


logger = logging.getLogger(__name__)

#URL_PROJECT_LIST = redirect('project:list')

@require_http_methods(['GET'])
@login_required
def addcontainer(request, userprojectbinding_id):
    """
    @summary: automagically create an environment
    @param usercoursebinding_id
    """
    from kooplexhub.lib.libbase import standardize_str
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        project = UserProjectBinding.objects.get(id = userprojectbinding_id, user = user).project
        container, created = Container.objects.get_or_create(
            name = f'generated for {project.name}', 
            label = f'project-{user.username}-{standardize_str(project.name)}',
            user = user,
            image = project.preferred_image
        )
        ProjectContainerBinding.objects.create(project = project, container = container)
        if created:
            messages.info(request, f'We created a new environment {container.name} for project {project.name}.')
        else:
            messages.info(request, f'We associated your project {project.name} with your former environment {container.name}.')
    except Exception as e:
        messages.error(request, f'We failed -- {e}')
        raise
    return redirect('container:list')



class ProjectView(LoginRequiredMixin):
    model = Project
    template_name = 'project_configure.html'
    form_class = FormProject
    success_url = '/hub/project/list/' #FIXME: django.urls.reverse or shortcuts.reverse does not work reverse('project:list')

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['user'] = user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('pk')
        context['menu_project'] = True
        context['submenu'] = 'configure' if project_id else 'new' 
        context['active'] = self.request.COOKIES.get('configure_project_tab', 'collaboration') if project_id else 'meta'
        context['url_post'] = reverse('project:configure', args = (project_id, )) if project_id else reverse('project:new')
        context['project_id'] = project_id
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        projectname = form.cleaned_data['name']
        subpath = form.cleaned_data['subpath']
        user = self.request.user
        project_config = form.cleaned_data.pop('project_config')
        assert user.id == project_config['user_id']
        project_id = project_config['project_id']
        msgs = []
        if project_id:
            project = Project.objects.get(id = project_id)
        else:
            project = Project.objects.create(**form.cleaned_data)
            UserProjectBinding.objects.create(user = user, project = project, role = UserProjectBinding.RL_CREATOR)
            msgs.append(f'Project {project} created.')
        container_add = []
        for container in project_config['bind_containers']:
            _, created = ProjectContainerBinding.objects.get_or_create(project = project, container = container)
            if created:
                container_add.append(str(container))
        if container_add:
            msgs.append('Project associated with container(s): {}.'.format(', '.join(container_add)))
        remove = ProjectContainerBinding.objects.filter(project = project).exclude(container__in = project_config['bind_containers'])
        remove.delete()
        if remove:
            msgs.append('Project disconnected from container(s): {}.'.format(', '.join([ str(b.container) for b in remove ])))
        collaborator_add = []
        for collaborator in project_config['collaborators']:
            role = UserProjectBinding.RL_ADMIN if collaborator in project_config['admins'] else UserProjectBinding.RL_COLLABORATOR
            b, created = UserProjectBinding.objects.get_or_create(user = collaborator, project = project)
            b.role = role
            b.save()
            if created:
                collaborator_add.append(str(collaborator))
        if collaborator_add:
            msgs.append('Collaborator(s) added to the project: {}.'.format(', '.join(collaborator_add)))
        remove = UserProjectBinding.objects.filter(project = project).exclude(user = user).exclude(user__in = project_config['collaborators'])
        remove.delete()
        if remove:
            msgs.append('Collaborator(s) removed from the project: {}.'.format(', '.join([ str(b.user) for b in remove ])))
        if msgs:
            messages.info(self.request, ' '.join(msgs))
        return super().form_valid(form)


class NewProjectView(ProjectView, generic.FormView):
    pass


class ConfigureProjectView(ProjectView, generic.edit.UpdateView):
    pass


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
        l = reverse('project:new')
        context = super().get_context_data(**kwargs)
        context['submenu'] = 'list'
        context['menu_project'] = True
        context['empty_title'] = "You have no projects"
        context['wss_container'] = KOOPLEX.get('hub', {}).get('wss_container', 'wss://localhost/hub/ws/container_environment/{userid}/').format(userid = self.request.user.id)
        context['wss_project'] = KOOPLEX.get('hub', {}).get('wss_project', 'wss://localhost/hub/ws/project/{userid}/').format(userid = self.request.user.id)
        context['empty_body'] = format_html(f"""You can create a <a href="{l}"><i class="bi bi-bag-plus"></i><span>&nbsp;new project</span></a>.""")
        context['n_hidden'] = len(context['object_list'].filter(is_hidden = True))
        return context

    def get_queryset(self):
        user = self.request.user
        projectbindings = UserProjectBinding.objects.filter(user = user).order_by('project__name')
        return projectbindings


class JoinProjectView(LoginRequiredMixin, generic.FormView):
    template_name = 'project_join.html'
    form_class = FormJoinProject
    success_url = '/hub/project/list/' #FIXME: django.urls.reverse or shortcuts.reverse does not work reverse('project:list')

    def get_initial(self):
        initial = super().get_initial()
        initial['user'] = self.request.user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_project'] = True
        context['submenu'] = 'join'
        return context

