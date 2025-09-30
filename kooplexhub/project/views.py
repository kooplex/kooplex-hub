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
from volume.tables import TableVolume
from hub.tables import TableUsers
from .models import Project, UserProjectBinding, ProjectContainerBinding
from container.models import Image, Container

from .conf import PROJECT_SETTINGS
from container.conf import CONTAINER_SETTINGS


logger = logging.getLogger(__name__)


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


@require_http_methods(['GET'])
@login_required
def delete_or_leave(request, project_id, pk_user):
    """Delete or leave a project."""
    user = request.user
    assert user.id == pk_user, "user mismatch"
    logger.debug("method: %s, project id: %s, user: %s" % (request.method, project_id, user))
    try:
        project = Project.get_userproject(pk = project_id, user = user)
    except Project.DoesNotExist:
        messages.error(request, 'Project does not exist')
        return redirect('project:list')
    upb = project.userbindings.filter(user = user).first()
    if upb.role == upb.Role.CREATOR:
        collab = []
        for upb_i in project.userbindings.exclude(user = user):
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
    template_name = 'project/list.html'
    context_object_name = 'userprojectbindinglist'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_project'] = True
        context['wss_container_control'] = CONTAINER_SETTINGS['wss']['control'].format(user = self.request.user)
        context['wss_project_join'] = PROJECT_SETTINGS['wss']['join'].format(user = self.request.user)
        context['wss_project_config'] = PROJECT_SETTINGS['wss']['config'].format(user = self.request.user)
        context['wss_project_users'] = PROJECT_SETTINGS['wss']['users'].format(user = self.request.user)
        context['wss_project_container'] = PROJECT_SETTINGS['wss']['containers'].format(user = self.request.user)
        context['n_hidden'] = len(context['object_list'].filter(is_hidden = True))
        context['images'] = Image.objects.filter(imagetype = Image.TP_PROJECT, present = True)
        context['users'] = [ u.profile._repr for u in User.objects.all().exclude(id = self.request.user.id) ]
        context['t_users'] = TableUsers(User.objects.all().exclude(id = self.request.user.id), marker_column='Admin')
        context['t_volume'] = TableVolume.for_user(self.request.user)
        return context

    def get_queryset(self):
        user = self.request.user
        projectbindings = UserProjectBinding.objects.filter(user = user).order_by('project__name')
        return projectbindings


