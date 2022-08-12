from django.urls import path, re_path

from . import views

app_name = 'volume'

urlpatterns = [
    path('new/', views.new, name = 'new'),
    re_path('delete/(?P<volume_id>\d+)/?$', views.delete_or_leave, name = 'delete'),
    #path('layoutflip/', views.layout_flip, name = 'layout_flip'),
    re_path('^configure/(?P<volume_id>\d+)/?', views.configure, name = 'configure'),

    #re_path('^info/(?P<volume_id>\d+)/?', views.refresh, name = 'refreshlogs'),

    path('volume/list', views.VolumeListView.as_view(), name = 'list'),
]
