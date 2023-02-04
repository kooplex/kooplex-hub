from django.urls import path, re_path

from . import views

app_name = 'container'

urlpatterns = [
    path('list/', views.ContainerListView.as_view(), name = 'list'),
    path('new/', views.NewContainerView.as_view(), name = 'new'),
    path('configure/<int:pk>/', views.ConfigureContainerView.as_view(), name = 'configure'),
    re_path('^delete/(?P<container_id>\d+)/?', views.destroy, name = 'destroy'),
    re_path('^open/(?P<container_id>\d+)/?', views.open, name = 'open'),
]
