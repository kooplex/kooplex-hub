from django.conf.urls import patterns, url, include

from .views import *

urlpatterns = [
    url(r'^', include('kooplex.hub.views.home')),
    url(r'^worksheets', include('kooplex.hub.views.worksheets')),
    url(r'^notebooks', include('kooplex.hub.views.notebooks')),
    
    #url(r'^containers', containers, name='containers'),
    #url(r'^spawn', spawn, name='spawn'),
]