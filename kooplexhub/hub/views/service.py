import logging

from django.contrib import messages
from django.conf.urls import url, include
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
#from django.contrib.auth.models import User
#from django.utils.html import format_html
#import django_tables2 as tables
#from django_tables2 import RequestConfig
#from django.utils.translation import gettext_lazy as _
#from django.db.models import Q
#
#from kooplex.lib import list_projects
#from kooplex.lib import list_libraries
#from kooplex.lib import now
#
#from hub.forms import FormProject
#from hub.forms import table_collaboration, T_JOINABLEPROJECT
#from hub.forms import table_volume
#from hub.forms import table_vcproject
#from hub.forms import table_fslibrary
#from hub.models import Project, UserProjectBinding, Volume
#from hub.models import Image
#from hub.models import Profile
#from hub.models import VCToken, VCProject, VCProjectProjectBinding, ProjectContainerBinding
#from hub.models import FSToken, FSLibrary, FSLibraryProjectBinding#, ProjectContainerBinding
#
#from django.utils.safestring import mark_safe
#
logger = logging.getLogger(__name__)


#@login_required
#def new(request):
#    logger.debug("user %s" % request.user)
#    user_id = request.POST.get('user_id')
#    try:
#        assert user_id is not None and int(user_id) == request.user.id, "user id mismatch: %s tries to save %s %s" % (request.user, request.user.id, request.POST.get('user_id'))
#        projectname = request.POST.get('name')
#        for upb in UserProjectBinding.objects.filter(user = request.user):
#            assert upb.project.name != projectname, "Not a unique name"
#        form = FormProject(request.POST)
#        form.save()
#        UserProjectBinding.objects.create(user = request.user, project = form.instance, role = UserProjectBinding.RL_CREATOR)
#        messages.info(request, 'Your new project is created')
#        return redirect('project:list')
#    except Exception as e:
#        logger.error("New project not created -- %s" % e)
#        messages.error(request, 'Creation of a new project is refused.')
#        return redirect('indexpage')
#        

def nothing(request):
    messages.error(request, 'NOT IMPLEMETED YET')
    return redirect('indexpage')

urlpatterns = [
    url(r'^filesync', nothing, name = 'filesync'), 
    url(r'^versioncontrol', nothing, name = 'versioncontrol'), 
]

