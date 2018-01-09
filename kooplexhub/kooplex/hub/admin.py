from django.conf.urls import patterns, url, include
from django.shortcuts import render
from django.http import HttpRequest, HttpResponseRedirect,HttpResponse
from django.template import RequestContext
from django.contrib import admin
from kooplex.hub.models.container import Container
from kooplex.hub.models.project import Project, UserProjectBinding
from kooplex.hub.models.report import Report
from kooplex.hub.models.mountpoint import MountPoint, MountPointProjectBinding, MountPointPrivilegeBinding
from kooplex.hub.models.user import User
from kooplex.hub.models.volume import Volume, VolumeProjectBinding
from kooplex.hub.views.notebooks import Refresh_database

# Register your models here.
@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    pass

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'path')
    pass

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator')
    pass

@admin.register(MountPoint)
class MountPointAdmin(admin.ModelAdmin):
    list_display = ('id', 'displayname', 'name', 'type', 'host_mountpoint', 'host_groupid')
    pass

@admin.register(MountPointProjectBinding)
class MountPointProjectBinding(admin.ModelAdmin):
    list_display = ('id', 'mountpoint', 'project', 'readwrite')
    pass

@admin.register(UserProjectBinding)
class UserProjectBinding(admin.ModelAdmin):
    list_display = ('id', 'project', 'hub_user')
    pass

@admin.register(MountPointPrivilegeBinding)
class MountPointPrivilegeBinding(admin.ModelAdmin):
    list_display = ('id', 'mountpoint', 'user', 'accessrights')
    pass

def reset_password(modeladmin, request, queryset):
    for hubuser in queryset:
        hubuser.pwgen()

reset_password.short_description = 'Reset Password'

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'gitlab_id')
    readonly_fields = ('uid', 'gid', 'gitlab_id', 'password')
    fieldsets = ( (None, { 'fields': ('username', ( 'first_name', 'last_name'), 'bio', 'position', 'location', 'email', 'user_permissions', 'uid', 'gid', 'gitlab_id', 'password') }),    )
    change_list_template = "admin/change_list_hubuser.html"
    actions = [reset_password, ]

    #def save_model(self, request, obj, form, changed):
    #    User = HubUser()
    #    User.create(request)
        # add your code here
    #    return super(HubUserAdmin, self).changelist_view(request)





@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'displayname')
    pass

@admin.register(VolumeProjectBinding)
class VolumeProjectBindingAdmin(admin.ModelAdmin):
    pass

#def admin_main(request):
#   pass

urlpatterns = [
 #url(r'^refresh_images', DockerImage.Refresh_database, name='refresh_images'),
]
