from django.urls import path, re_path

from . import views

app_name = 'volume'

urlpatterns = [
    path('list', views.VolumeListView.as_view(), name = 'list'),
    path('attachment_new/', views.NewAttachmentView.as_view(), name = 'new_attachment'),
]
