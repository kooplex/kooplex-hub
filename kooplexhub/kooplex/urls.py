"""
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def indexpage(request):
    return render(request, 'index.html', {})

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^admin/', include('hub.admin', namespace = 'myadmin')),
    url(r'^hub/oauth/', include('social_django.urls', namespace = 'social')),
    url(r'^hub/container/', include('hub.views.container', namespace = 'container')),
    url(r'^hub/project/', include('hub.views.project', namespace = 'project')),
    url(r'^hub/teaching/', include('hub.views.teaching', namespace = 'teaching')),
    url(r'^hub/course/', include('hub.views.courses', namespace = 'course')),
    url(r'^hub/assignment/', include('hub.views.assignment', namespace = 'assignment')),
    url(r'^hub/user/', include('hub.views.user', namespace = 'user')),
    url(r'^hub/?', indexpage, name = 'indexpage'),
    url(r'^accounts/logout/', auth_views.logout, { 'next_page': 'indexpage' }, name = 'logout'),
]
