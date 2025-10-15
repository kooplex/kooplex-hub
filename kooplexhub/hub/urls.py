from django.urls import path, include
from django.contrib.auth import views as ca_views
from django.views.generic import RedirectView

from . import views

from kooplexhub import settings

urlpatterns = [
    path('oauth/', include('social_django.urls', namespace = 'social')),
    path('logout/', ca_views.LogoutView.as_view(), name = 'logout'),
    path('', RedirectView.as_view(pattern_name=settings.LOGOUT_REDIRECT_URL, permanent=False), name = 'indexpage'),
    path('monitoring/', views.MonitoringView.as_view(), name = 'monitoring'),
    path('usertokens/', views.UserTokenView.as_view(), name = 'usertokens'),
]
