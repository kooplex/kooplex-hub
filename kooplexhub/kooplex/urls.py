"""
"""
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from kooplex.settings import LOGOUT_URL

def indexpage(request):
    return render(request, 'index.html', { 'next_page': 'indexpage' })

@login_required
def do_logout(request):
    return redirect(LOGOUT_URL) #FIXME: add urlarg redirect_url=


urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^hub/oauth/', include('social_django.urls', namespace = 'social')),

    url(r'^hub/logout/', do_logout, name = 'do_logout'),
    
    url(r'^hub/mock/', include('kooplex.mock', namespace = 'mock')), #FIXME: REMOVE FROM PRODUCTION


    url(r'^hub/project/', include('hub.views.project', namespace = 'project')),
    url(r'^hub/report/', include('hub.views.report', namespace = 'report')),
    url(r'^hub/education/', include('hub.views.education', namespace = 'education')),
    url(r'^hub/assignment/', include('hub.views.assignment', namespace = 'assignment')),
    url(r'^hub/service/', include('hub.views.service', namespace = 'service')),
    url(r'^hub/volume/', include('hub.views.volume', namespace = 'volume')),
    url(r'^hub/external/', include('hub.views.external_service', namespace = 'service_external')),
    url(r'^hub/user/', include('hub.views.user', namespace = 'user')),
    url(r'^hub/?', indexpage, name = 'indexpage'),
    url(r'^accounts/logout/', auth_views.logout, { 'next_page': 'indexpage' }, name = 'logout'),
]


