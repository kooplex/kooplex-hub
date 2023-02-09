from django.urls import path, re_path

from . import views

app_name = 'report'

urlpatterns = [
    path('list/', views.ReportListView.as_view(), name = 'list'),
    path('new/', views.NewReportView.as_view(), name = 'new'),
    path('configure/<int:pk>/', views.ConfigureReportView.as_view(), name = 'configure'),
    re_path('delete/(?P<report_id>\d+)/?', views.delete, name = 'delete'),
    re_path('open/(?P<report_id>\d+)/?$', views.open, name = 'open'),
]
