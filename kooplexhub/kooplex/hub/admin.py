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
from kooplex.hub.models.mountpoints import MountPoints, MountPointProjectBinding, MountPointPrivilegeBinding
from kooplex.hub.models.user import HubUser
from kooplex.hub.models.volume import Volume, VolumeProjectBinding
from kooplex.hub.views.notebooks import Refresh_database

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

    def Refresh_database(self, request='', *args, **kwargs):
         from kooplex.lib.smartdocker import Docker
         from kooplex.hub.models.dashboard_server import Dashboard_server
         from kooplex.lib.libbase import get_settings

         d = Docker()
         notebook_images = d.get_all_notebook_images()
         for image in notebook_images:
             i = DockerImage()
             i = i.from_docker_dict(image)
             i.save()
             dashboards_prefix = get_settings('dashboards', 'prefix', None, '')
             notebook_prefix = get_settings('prefix', 'name', None, '')
             dashboard_container_name = dashboards_prefix + "_dashboards-" + \
                                        i.name.split(notebook_prefix + "-notebook-")[1]
             docker_container = d.get_container(dashboard_container_name, original=True)
             # container, docker_container = d.get_container(dashboard_container_name)
             if docker_container:
                 D = Dashboard_server()
                 D.init(d, docker_container)
                 D.save()
         return HttpResponseRedirect("/admin")

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
    list_display = ('id', 'name', 'type', 'host_mountpoint', 'host_groupid')
    pass

@admin.register(MountPointProjectBinding)
class MountPointProjectBinding(admin.ModelAdmin):
    list_display = ('id', 'mountpoint', 'project', 'readwrite')
    pass

@admin.register(MountPointPrivilegeBinding)
class MountPointPrivilegeBinding(admin.ModelAdmin):
    list_display = ('id', 'mountpoint', 'user', 'accessrights')
    pass

@admin.register(HubUser)
class HubUserAdmin(admin.ModelAdmin):
    list_display = ('gitlab_id','username')
    pass

@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ('name', )
    pass

@admin.register(VolumeProjectBinding)
class VolumeProjectBindingAdmin(admin.ModelAdmin):
    pass

def admin_main(request):
   pass

urlpatterns = [
 url(r'^refresh_images', DockerImageAdmin.Refresh_database, name='refresh_images'),
]
