from django.urls import path, re_path

from . import views

app_name = 'report'

urlpatterns = [
    #path('new/', views.NewReportView.as_view(), name = 'new'),
    path('new/', views.new, name = 'new'),
    path('create/', views.create, name = 'create'),
    path('list/', views.ReportListView.as_view(), name = 'list'),
    path('unlist/', views.ReportListView.as_view(), name = 'unlist'),
    re_path('delete/(?P<report_id>\d+)/?', views.delete, name = 'delete'),
    re_path('configure/(?P<report_id>\d+)/?$', views.configure, name = 'configure'),
    re_path('open/(?P<report_id>\d+)/?$', views.open, name = 'open'),
    path('modify/', views.modify, name = 'modify'),
]
