from django.urls import path, include
from django.contrib.auth import views as ca_views

from . import views

#TEST MIATT
from django.urls import re_path

urlpatterns = [
    path('oauth/', include('social_django.urls', namespace = 'social')),
    path('logout/', ca_views.LogoutView.as_view(), name = 'logout'),
    path('', views.IndexView.as_view(), name = 'indexpage'),
    path('monitoring/', views.MonitoringView.as_view(), name = 'monitoring'),

    #JUST FOR THE TEST TASK
#    re_path('cel/(?P<duma>\w+)/?$', views.task, name = 'testtask'),
]
#TODO: custom 403 view https://docs.djangoproject.com/en/3.2/topics/http/views/
