from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^projects', views.projects, name='projects'),
    url(r'^containers', views.containers, name='containers'),
    url(r'^spawn', views.spawn, name='spawn'),
]