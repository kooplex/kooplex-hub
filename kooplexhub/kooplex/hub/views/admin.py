from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest
from django.template import RequestContext
from datetime import datetime
from django.http import HttpRequest, HttpResponseRedirect
from kooplex.hub.forms import BootstrapAuthenticationForm


from kooplex.lib.libbase import get_settings
from kooplex.lib.gitlab import Gitlab
from kooplex.lib.gitlabadmin import GitlabAdmin
from kooplex.lib.spawner import Spawner
from kooplex.lib.dashboards import Dashboards
from kooplex.lib.debug import *

DEBUG = True
ACCESS_LEVELS = { 40 : 'Master',\
                    30 : 'Developer',\
                    20 : 'Reporter',\
                    10 : 'Guest',\
                    50 : 'Owner'}

ADMIN_URL = '/hub/admin'

def admin_home(request):
    """Renders the worksheets page"""
    assert isinstance(request, HttpRequest)
    username = request.user.username

    users=[]
#    g = Gitlab(request)
#    projects, unforkable_projectids = g.get_projects()
    gadmin = GitlabAdmin(request)
    projects = gadmin.get_all_projects()
    isadmin = gadmin.check_useradmin(username)
    users = gadmin.get_all_users()
    for project in projects:
        members = gadmin.get_project_members(project['id'])
        project['members'] = []
        for member in members:
            project['members'].append({'name':member['username'],'id':member['id'], 'access':ACCESS_LEVELS[member['access_level']]})

    groups = gadmin.get_all_groups()    
    
    for group in groups:
        print(group)
        members = gadmin.get_group_members(group['id'])
        group['members'] = []
        for member in members:
            group['members'].append({'name':member['username'],'id':member['id'], 'access':ACCESS_LEVELS[member['access_level']]})
    
    return render(
        request,
        'app/admin.html',
        context_instance = RequestContext(request,
        {
            'title':'Admin',
            'message':'',
            'users': users,
            'projects': projects,
            'username': username,
            'groups': groups,
            'admin': isadmin,
            'authentication_form': BootstrapAuthenticationForm,
       })
    )


def add_user(request):
    username = request.GET['user_name']
    firstname = request.GET['first_name']
    lastname = request.GET['last_name']
    email = request.GET['email']
    password = request.GET['password']
    u = User(
        username=username,
        first_name=firstname,
        last_name=lastname,
        email=email
    )
    u.password = password
    return HttpResponseRedirect(url)

urlpatterns = [
    url(r'^$', admin_home, name='admin'),
    url(r'^$add_user', add_user, name='add_user')
]