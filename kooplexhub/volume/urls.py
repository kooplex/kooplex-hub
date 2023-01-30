from django.urls import path, re_path

from . import views

app_name = 'volume'

urlpatterns = [
    path('list', views.VolumeListView.as_view(), name = 'list'),
    path('attachment_new/', views.NewAttachmentView.as_view(), name = 'new_attachment'),
#    re_path('delete/(?P<volume_id>\d+)/?$', views.delete_or_leave, name = 'delete'),
    path('configure/<int:pk>/', views.ConfigureVolumeView.as_view(), name = 'configure'),
]
