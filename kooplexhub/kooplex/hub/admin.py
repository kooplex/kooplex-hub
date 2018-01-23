import logging

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
#FIXME: deletion of many should be caugth and iterated like the sigle instance in the delete_model method!!!
    actions = ['reset_password', ]

    def reset_password(self, request, queryset):
        for user in queryset:
            user.generatenewpassword()
    reset_password.short_description = 'Reset password'

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
        if user.n_projects > 0 or user.n_reports > 0:
            # policy? delete reports and projects OR delegate to a dummy user?
            raise NotImplementedError
        user.remove()
        super().delete_model(request, user)

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

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
    init_containertypes()
    init_scopetypes()
    return redirect('/admin')

urlpatterns = [
    url(r'^refreshimages', refreshimages, name = 'refresh-images'),
    url(r'^initmodel', initmodel, name = 'init-model'),
]

