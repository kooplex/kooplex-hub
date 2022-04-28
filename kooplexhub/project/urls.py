from django.urls import path, re_path

from . import views

app_name = 'project'

urlpatterns = [
    path('new/', views.new, name = 'new'),
    re_path('delete/(?P<project_id>\d+)/?$', views.delete_or_leave, name = 'delete'),
    path('list/', views.UserProjectBindingListView.as_view(), name = 'list'),
    path('join/', views.join, name = 'join'),
    path('layoutflip/', views.layout_flip, name = 'layout_flip'),
    re_path('hide/(?P<project_id>\d+)/?$', views.hide, name = 'hide'),
    re_path('show/(?P<project_id>\d+)/?$', views.show, name = 'show'),
    path('showhide/', views.show_hide, name = 'showhide'),
    re_path('configure/(?P<project_id>\d+)/?$', views.configure, name = 'configure'),
]
