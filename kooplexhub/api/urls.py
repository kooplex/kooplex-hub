from django.urls import path, re_path

from api import views

app_name = 'api'

urlpatterns = [
    path('version/', views.version, name = 'version'),
    path('images/', views.images, name = 'images'),
    path('projects/', views.projects, name = 'projects'),
    path('volumes/', views.volumes, name = 'volumes'),
    path('nodes/', views.nodes, name = 'nodes'),
    re_path('submit/(?P<job_name>\w+)/', views.submit, name = 'submit'),
    re_path('info/(?P<job_name>\w+)/', views.info, name = 'info'),
    re_path('log/(?P<job_name>\w+)/', views.log, name = 'log'),
    re_path('delete/(?P<job_name>\w+)/', views.delete, name = 'delete'),
]
