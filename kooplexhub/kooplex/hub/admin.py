from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponseRedirect,HttpResponse
from django.template import RequestContext
from django.contrib import admin

from kooplex.hub.models import *


# Register your models here.
@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner')

@admin.register(HtmlReport)
class HtmlReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator')

@admin.register(DashboardReport)
class DashboardReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator')

@admin.register(MountPoint)
class MountPointAdmin(admin.ModelAdmin):
    list_display = ('id', 'displayname', 'name', 'type', 'host_mountpoint', 'host_groupid')

@admin.register(MountPointProjectBinding)
class MountPointProjectBinding(admin.ModelAdmin):
    list_display = ('id', 'mountpoint', 'project', 'readwrite')

@admin.register(UserProjectBinding)
class UserProjectBinding(admin.ModelAdmin):
    list_display = ('id', 'project', 'user')

@admin.register(MountPointPrivilegeBinding)
class MountPointPrivilegeBinding(admin.ModelAdmin):
    list_display = ('id', 'mountpoint', 'user', 'accessrights')

def reset_password(modeladmin, request, queryset):
    for hubuser in queryset:
        hubuser.pwgen()

reset_password.short_description = 'Reset Password'

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'gitlab_id')
    readonly_fields = ('uid', 'gid', 'gitlab_id', 'password')
    fieldsets = ( (None, { 'fields': ('username', ( 'first_name', 'last_name'), 'bio', 'email', 'user_permissions', 'uid', 'gid', 'gitlab_id', 'password') }),    )
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

@admin.register(VolumeProjectBinding)
class VolumeProjectBindingAdmin(admin.ModelAdmin):
    pass

#def admin_main(request):
#   pass

def refreshimages(request):
#FIXME: authorize
    refresh_images()
    return redirect('/admin')

def initmodel(request):
#FIXME: authorize
    init_containertypes()
    init_scopetypes()
    return redirect('/admin')

urlpatterns = [
    url(r'^refreshimages', refreshimages, name = 'refresh-images'),
    url(r'^initmodel', initmodel, name = 'init-model'),
]

