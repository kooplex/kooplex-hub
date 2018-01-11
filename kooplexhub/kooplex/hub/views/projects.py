from django.conf.urls import patterns, url, include
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.http import HttpRequest#, HttpResponseRedirect,HttpResponse
from django.template import RequestContext

from kooplex.hub.models.image import Image
from kooplex.hub.models.project import Project, UserProjectBinding
from kooplex.hub.models.user import User
from kooplex.hub.models.scope import ScopeType

##import logging
##logger = logging.getLogger(__name__)
##debug_logger = logging.getLogger('debug_logger')
##info_logger = logging.getLogger('info_logger')
##import git
##import json
##import logging
##import logging.config
##import os.path
##from distutils.dir_util import remove_tree
##import pwgen
##import re
##from datetime import datetime
##from django.contrib.auth.models import User
##from django.shortcuts import render
##from django.template.response import TemplateResponse
##
##from kooplex.hub.models.mountpoint import MountPoint, MountPointProjectBinding, MountPointPrivilegeBinding
###from kooplex.hub.models.notebook import Notebook
##from kooplex.hub.models.report import Report
###from kooplex.hub.models.session import Session
##from kooplex.hub.models.volume import Volume, VolumeProjectBinding
##from kooplex.lib.gitlab import Gitlab
##from kooplex.lib.gitlabadmin import GitlabAdmin
##from kooplex.lib.jupyter import Jupyter
##from kooplex.lib.libbase import LibBase
##from kooplex.lib.libbase import get_settings,  mkdir
##
##from kooplex.lib.ochelper import OCHelper
##from kooplex.lib.repo import Repo  # GONNA BE OBSOLETED
##from kooplex.lib.repository import repository
##from kooplex.lib.sendemail import send_new_password
##from kooplex.lib.smartdocker import Docker
##from kooplex.lib.spawner import Spawner
##
##from kooplex.lib.ldap import Ldap
##import subprocess
##
##NOTEBOOK_DIR_NAME = 'notebooks'
##HUB_NOTEBOOKS_URL = '/hub/notebooks'
##
##from kooplex.lib.debug import *

def projects(request, *v, **kw):
    """Renders the notebooks page"""
    assert isinstance(request, HttpRequest)
    if request.user.is_anonymous():
        return redirect(reverse('login'))

    PUBLIC = ScopeType.objects.get(name = 'public')
    user = User.objects.get(username = request.user.username)
    projects_mine = Project.objects.filter(owner = user)
    projects_sharedwithme = sorted([ upb.project for upb in UserProjectBinding.objects.filter(user = user) ])
    projects_public = sorted(Project.objects.filter(scope = PUBLIC).exclude(owner = user))
    images = Image.objects.all()
    scopes = ScopeType.objects.all()
#FIXME:
#volumes

    return render(
        request,
        'project/projects.html',
        context_instance = RequestContext(request,
        {
            'user': user,
            'projects_mine': projects_mine,
            'projects_shared': projects_sharedwithme,
            'projects_public': projects_public,
            'images' : images,
            'scopes' : scopes,
            'errors' : kw.get('error', None),
            'year' : 2018,
        })
    )

urlpatterns = [
    url(r'^/?$', projects, name = 'projects'),
    url(r'^/new$', projects, name = 'project-new'), #FIXME:
    url(r'^/configure$', projects, name = 'project-settings'), #FIXME:
    url(r'^/revisioncontrol$', projects, name = 'project-commit'), #FIXME:
    url(r'^/collaborate$', projects, name = 'project-members-form'), #FIXME:

    url(r'^/start$', projects, name = 'container-start'), #FIXME:
]
