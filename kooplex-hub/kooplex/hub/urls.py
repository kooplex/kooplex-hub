from django.conf.urls import url

from .views import *

urlpatterns = [
    url(r'^$', home.index, name='home'),
    url(r'^contact$', home.contact, name='contact'),
    url(r'^about', home.about, name='about'),

    #url(r'^projects', projects, name='projects'),
    #url(r'^containers', containers, name='containers'),
    #url(r'^spawn', spawn, name='spawn'),
]