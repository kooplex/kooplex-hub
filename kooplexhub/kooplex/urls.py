"""
Definition of urls for kooplex.
"""

from django.conf.urls import url, include
from django.contrib import admin
admin.autodiscover()

urlpatterns = [
    url(r'^hub', include('kooplex.hub.urls')),
## ##    #url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^admin/', include('kooplex.hub.admin')),
]
