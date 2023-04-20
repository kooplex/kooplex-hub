"""kooplexhub URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('hub/container_environment/', include('container.urls', namespace = 'container')),
    path('hub/project/', include('project.urls', namespace = 'project')),
    path('hub/report/', include('report.urls', namespace = 'report')),
    path('hub/education/', include('education.urls', namespace = 'education')),
    path('hub/volume/', include('volume.urls', namespace = 'volume')),
    path('hub/api/', include('api.urls')),
    path('hub/', include('hub.urls')),
    path('admin/', admin.site.urls),
]
