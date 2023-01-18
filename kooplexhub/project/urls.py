from django.urls import path, re_path

from . import views

app_name = 'project'

urlpatterns = [
    path('new/', views.NewProjectView.as_view(), name = 'new'),
    re_path('delete/(?P<project_id>\d+)/?$', views.delete_or_leave, name = 'delete'),
    path('list/', views.UserProjectBindingListView.as_view(), name = 'list'),
    path('join/', views.join, name = 'join'),
    re_path('configure/(?P<project_id>\d+)/?$', views.configure, name = 'configure'),
    path('configure_save/', views.configure_save, name = 'configure_save'),
]
