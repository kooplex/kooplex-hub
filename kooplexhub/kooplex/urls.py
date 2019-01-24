"""
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def indexpage(request):
    return render(request, 'index.html', { 'next_page': 'indexpage' })

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    
    url(r'^hub/mock/', include('kooplex.mock', namespace = 'mock')), #FIXME: REMOVE FROM PRODUCTION

    url(r'^hub/oauth/', include('social_django.urls', namespace = 'social')),
    url(r'^hub/project/', include('hub.views.project', namespace = 'project')),
    url(r'^hub/education/', include('hub.views.education', namespace = 'education')),
    url(r'^hub/assignment/', include('hub.views.assignment', namespace = 'assignment')),
    url(r'^hub/container/', include('hub.views.container', namespace = 'container')),
    url(r'^hub/user/', include('hub.views.user', namespace = 'user')),
    url(r'^hub/?', indexpage, name = 'indexpage'),
    url(r'^accounts/logout/', auth_views.logout, { 'next_page': 'indexpage' }, name = 'logout'),
]
