from django.contrib import admin
#from django import forms

from .models import *


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'present', 'name', 'imagetype', 'description', 'require_home', 'mount_project', 'mount_report')
    search_labels = ('name', 'imagetype')
    search_fields = ('name', 'imagetype', 'description' )

    def enable_image(self, request, queryset):
        for obj in queryset:
            obj.present = True
            obj.save()

    def disable_image(self, request, queryset):
        for obj in queryset:
            obj.present = False
            obj.save()

    actions = [enable_image, disable_image]

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'label', 'image', 'state', 'launched_at', 'restart_reasons')
    search_labels = ('name', 'user__username')

    def start_container(self, request, queryset):
        for obj in queryset:
            obj.start()

    def stop_container(self, request, queryset):
        for obj in queryset:
            obj.stop()
    start_container.short_description = "Start container"

    actions = [start_container, stop_container]

@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'default', 'token_as_argument', 'port')
    search_fields = ('image__name', 'name', 'port')

@admin.register(EnvVarMapping)
class EnvVarMappingAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'name', 'valuemap')
    search_labels = ('image__name', 'name')
    search_fields = ('image__name', 'name')
