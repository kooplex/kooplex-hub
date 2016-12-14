from django.conf.urls import patterns, url, include

from .views import *

urlpatterns = [
    url(r'^', include('kooplex.hub.views.home')),
    url(r'^worksheets', include('kooplex.hub.views.worksheets')),
    url(r'^notebooks', include('kooplex.hub.views.notebooks')),
    url(r'^list', include('kooplex.hub.views.upload')),
    url(r'^admin', include('kooplex.hub.views.admin')),
    url(r'^changepassword', include('kooplex.hub.views.changepassword')),
    #url(r'^changepasswordform',include('kooplex.hub.views.changepassword')),

    
    #url(r'^containers', containers, name='containers'),
    #url(r'^spawn', spawn, name='spawn'),
]