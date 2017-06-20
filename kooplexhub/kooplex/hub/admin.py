from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect,HttpResponse
from django.template import RequestContext
from django.contrib import admin
from kooplex.hub.models.notebook import Notebook
from kooplex.hub.models.session import Session
from kooplex.hub.models.container import Container
from kooplex.hub.models.dashboard_server import Dashboard_server
from kooplex.hub.models.dockerimage import DockerImage
from kooplex.hub.models.project import Project
from kooplex.hub.models.report import Report
from kooplex.hub.models.mountpoints import MountPoints
from kooplex.hub.models.user import HubUser


# Register your models here.
@admin.register(Notebook)
class NotebookAdmin(admin.ModelAdmin):
    pass

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    pass

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    pass

@admin.register(DockerImage)
class DockerImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    pass

@admin.register(Dashboard_server)
class Dashboard_serverAdmin(admin.ModelAdmin):
    list_display = ('name', 'docker_port')
    pass

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner_username','owner_name', 'path', 'visibility')
    pass

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator_name', 'file_name', 'type')
    pass

@admin.register(MountPoints)
class MountPoints(admin.ModelAdmin):
    list_display = ('id', 'name', 'project_id', 'type', 'host_mountpoint', 'container_mountpoint')
    pass

@admin.register(HubUser)
class HubUserAdmin(admin.ModelAdmin):
    list_display = ('gitlab_id','username')
    pass

def admin_main(request):
    print("Hello")
    vmi=[]
    return render(
        request,
        'app/admin.html',
        context_instance=RequestContext(request,
                                        {
                                            'vmi' : vmi,
                                        })
    )


urlpatterns = [
 url(r'^', admin_main, name='admin_main'),
]