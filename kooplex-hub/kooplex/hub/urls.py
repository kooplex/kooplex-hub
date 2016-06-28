from django.conf.urls import patterns, url, include

from .views import *

urlpatterns = [
    url(r'^', include('kooplex.hub.views.home')),
    url(r'^projects', include('kooplex.hub.views.projects')),
    
    #url(r'^containers', containers, name='containers'),
    #url(r'^spawn', spawn, name='spawn'),
]