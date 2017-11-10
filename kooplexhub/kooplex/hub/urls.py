from django.conf.urls import url, include

from .views import *
from django.shortcuts import render


def tutorial(request):
    return render(request, 'app/tutorial.html')

urlpatterns = [
    url(r'^', include('kooplex.hub.views.home')),
    url(r'^reports/', include('kooplex.hub.views.reports')),
    url(r'^notebooks', include('kooplex.hub.views.notebooks')),
    url(r'^list', include('kooplex.hub.views.upload')),
    url(r'^changepassword', include('kooplex.hub.views.changepassword')),
    url(r'^tutorial', tutorial, name="tutorial"),
]
