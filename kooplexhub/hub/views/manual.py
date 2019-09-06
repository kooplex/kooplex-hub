import logging

from django.conf.urls import url
from django.shortcuts import redirect, render

from kooplex.settings import DOMAIN

logger = logging.getLogger(__name__)

def man_login(request):
    return render(request, 'manual/login.html',  { 'submenu': 'login', 'next_page': 'indexpage' })

def man_folder(request):
    return render(request, 'manual/folders.html',  { 'submenu': 'folders', 'next_page': 'indexpage' })

def man_issues(request):
    return render(request, 'manual/issues.html',  { 'submenu': 'issues', 'next_page': 'indexpage' })

def man_concepts(request):
    return render(request, 'manual/concepts.html',  { 'submenu': 'concepts', 'next_page': 'indexpage' })

def man_compute(request):
    return render(request, 'manual/compute.html',  { 'submenu': 'compute', 'next_page': 'indexpage' })

def man_projects(request):
    return render(request, 'manual/projects.html',  { 'submenu': 'projects', 'next_page': 'indexpage' })

def man_reports(request):
    return render(request, 'manual/reports.html',  { 'submenu': 'reports', 'next_page': 'indexpage' })

urlpatterns = [
    url(r'^login/?$', man_login, name = 'login'),
    url(r'^folder/?$', man_folder, name = 'folder'),
    url(r'^issues/?$', man_issues, name = 'issues'),
    url(r'^concepts/?$', man_concepts, name = 'concepts'),
    url(r'^compute/?$', man_compute, name = 'compute'),
    url(r'^projects/?$', man_projects, name = 'projects'),
    url(r'^reports/?$', man_reports, name = 'reports'),
]

