from django.urls import path, re_path

from . import views

app_name = 'container'

urlpatterns = [
    path('new/', views.NewContainerView.as_view(), name = 'new'),
    re_path('^delete/(?P<container_id>\d+)/?', views.destroy, name = 'destroy'),
    path('list/', views.ContainerListView.as_view(), name = 'list'),
    path('reportclist/', views.ReportContainerListView.as_view(), name = 'reportclist'), #FIXME: ez mi?
    re_path('^configure/(?P<container_id>\d+)/?', views.configure, name = 'configure'),
    path('configure_save/', views.configure_save, name = 'configure_save'),
#DEPRECATED     re_path('^start/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)/?', views.start, name = 'start'),
#DEPRECATED     re_path('^stop/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)/?', views.stop, name = 'stop'),
#DEPRECATED     re_path('^restart/(?P<container_id>\d+)/(?P<next_page>\w+:?\w*)/?', views.restart, name = 'restart'),
    re_path('^open/(?P<container_id>\d+)/?', views.open, name = 'open'),
]
