from django.conf.urls import patterns, url, include
from django.contrib import admin
admin.autodiscover()

from .views import *

urlpatterns = [
    url(r'^', include('kooplex.hub.views.home')),
    url(r'^worksheets', include('kooplex.hub.views.worksheets')),
    url(r'^notebooks', include('kooplex.hub.views.notebooks')),
    url(r'^list', include('kooplex.hub.views.upload')),
    url(r'^changepassword', include('kooplex.hub.views.changepassword')),
    url(r'^admin/', admin.site.urls),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    #url(r'^changepasswordform',include('kooplex.hub.views.changepassword')),

    
    #url(r'^containers', containers, name='containers'),
    #url(r'^spawn', spawn, name='spawn'),
]