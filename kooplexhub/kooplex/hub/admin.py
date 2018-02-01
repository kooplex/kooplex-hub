import logging

from django.contrib import messages
from django.conf.urls import patterns, url, include
from django.shortcuts import render, redirect
from django.http import HttpRequest, HttpResponseRedirect,HttpResponse
from django.template import RequestContext
from django.contrib import admin
from django import forms

from kooplex.hub.models import *

logging.getLogger(__name__)

U = User

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'uid', 'gitlab_id', 'n_projects', 'n_reports')
    #fieldsets = ( (None, { 'fields': (( 'first_name', 'last_name'), ('username', 'email'), 'bio', 'user_permissions') }),    )
    fieldsets = ( (None, { 'fields': (( 'first_name', 'last_name'), ('username', 'email'), 'bio' ) }),    )
    actions = ['reset_password', 'remove_users' ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['messages'] = messages.get_messages(request)
        return super(UserAdmin, self).changelist_view(request, extra_context)
        
    def reset_password(self, request, queryset):
        msg = ""
        for user in queryset:
            user.generatenewpassword()
            msg += "%s, " % user.username
        messages.success(request,"Password reseted for: %s" % msg)
    reset_password.short_description = 'Reset password'

    def remove_users(self, request, queryset):
        msg = ""
        oops = ""
        for user in queryset:
            try:
                user.remove()
                super().delete_model(request, user)
                msg += "%s, " % user
            except Exception as e:
                oops += "%s (%s), " % (user, e)
        if len(msg):
            messages.success(request,"Deleted: %s" % msg)
        if len(oops):
            messages.warning(request,"Ooopsed: %s" % oops)
    remove_users.short_description = 'Delete users in a neat way'

    def save_model(self, request, user, form, changed):
        try:
            user_old = User.objects.get(username = user.username)
            if user_old.email != user.email:
                # user.changeemail()  #TODO: if e-mail may change then gitlab user details have to be updated accordingly
                raise NotImplementedError
        except User.DoesNotExist:
            user.create()
        super().save_model(request, user, form, changed)

    def delete_model(self, request, user):
        user.remove()
        super().delete_model(request, user)

@admin.register(ProjectContainer)
class ProjectContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'project')

@admin.register(DashboardContainer)
class DashboardContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'report', 'uptime', 'url')
    actions = ['stop_containers', ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def stop_containers(self, request, queryset):
        from kooplex.logic.spawner import stop_container
        msg = ""
        oops = ""
        for container in queryset:
            try:
                stop_container(container)
                msg += "%s, " % container
            except:
                oops += "%s, " % container
        if len(msg):
            messages.success(request, "stopped: %s" % msg)
        if len(oops):
            messages.warning(request, "oopses: %s" % oops)
    stop_containers.short_description = 'Stop selected containers'

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'owner', 'gitlab_id')

@admin.register(HtmlReport)
class HtmlReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator')

@admin.register(DashboardReport)
class DashboardReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'creator')

@admin.register(UserProjectBinding)
class UserProjectBinding(admin.ModelAdmin):
    list_display = ('id', 'project', 'user')

@admin.register(FunctionalVolume)
class FunctionalVolumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'displayname', 'description', 'owner')

@admin.register(StorageVolume)
class StorageVolumeAdmin(admin.ModelAdmin):
    list_display = ('name', 'displayname', 'description', 'groupid')

@admin.register(VolumeProjectBinding)
class VolumeProjectBindingAdmin(admin.ModelAdmin):
    pass

#def admin_main(request):
#   pass

def refreshimages(request):
#FIXME: authorize
    refresh_images()
    refresh_volumes()
    return redirect('/admin')

def initmodel(request):
#FIXME: authorize
#    init_containertypes()
    init_scopetypes()
    return redirect('/admin')

urlpatterns = [
    url(r'^refreshimages', refreshimages, name = 'refresh-images'),
    url(r'^initmodel', initmodel, name = 'init-model'),
]

