from django.urls import path, re_path

from . import views

app_name = 'project'

urlpatterns = [
    path('list/', views.UserProjectBindingListView.as_view(), name = 'list'),
    path('new/', views.NewProjectView.as_view(), name = 'new'),
    path('configure/<int:pk>/', views.ConfigureProjectView.as_view(), name = 'configure'),
    path('join/', views.JoinProjectView.as_view(), name = 'join'),
    re_path('delete/(?P<project_id>\d+)/?$', views.delete_or_leave, name = 'delete'),
]
