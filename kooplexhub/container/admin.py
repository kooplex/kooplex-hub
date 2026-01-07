from django.contrib import admin
#from django import forms

from .models import *


@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'present', 'name', 'show_thumbnail', 'imagetype', 'description', 'require_home', 'mount_project', 'mount_report', 'liveness_probe')
    search_labels = ('name', 'imagetype')
    search_fields = ('name', 'imagetype', 'description' )
    def show_thumbnail(self, instance):
        return instance.thumbnail.to_html if instance.thumbnail else '-'
    def enable_image(self, request, queryset):
        for obj in queryset:
            obj.present = True
            obj.save()
    def disable_image(self, request, queryset):
        for obj in queryset:
            obj.present = False
            obj.save()
    actions = [enable_image, disable_image]

@admin.register(Liveness_Probe)
class Liveness_ProbeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'method', 'path', 'port', 'initial_delay_seconds', 'period_seconds')
    search_labels = ('method', 'path')
    search_fields = ('method', 'path')

@admin.register(ServiceView)
class ServiceViewAdmin(admin.ModelAdmin):
    def endpoint(self, instance):
        return instance.proxy.svc_endpoint
    def show_icon(self, instance):
        return instance.icon.to_html if instance.icon else '-'
    list_display = ('id', 'name', 'suffix', 'show_icon', 'openable', 'pass_token', 'url', 'endpoint')
    search_labels = ('name', 'suffix')
    search_fields = ('name', 'suffix')


@admin.register(ProxyImageBinding)
class ProxyImageBindingAdmin(admin.ModelAdmin):
    def proxyname(self, instance):
        return instance.proxy.name
    list_display = ('id', 'image', 'proxyname')


@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'label', 'image', 'state', 'launched_at', 'restart_reasons')
    search_labels = ('name', 'user__username')
    search_fields = ('name', 'user__username', 'label', 'image__name')

    def start_container(self, request, queryset):
        for obj in queryset:
            obj.start()
    start_container.short_description = "Start container"

    def stop_container(self, request, queryset):
        for obj in queryset:
            obj.stop()
    stop_container.short_description = "Stop container"

    def restart_container(self, request, queryset):
        for obj in queryset:
            obj.stop()
    restart_container.short_description = "Restart container"

    actions = [start_container, restart_container, stop_container]

@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    def bound_images(self, instance):
        return len(ProxyImageBinding.objects.filter(proxy=instance))
    list_display = ('id', 'name', 'svc_port', 'register', 'views', 'bound_images')
    search_fields = ('image__name', 'name', 'port')

@admin.register(EnvVarMapping)
class EnvVarMappingAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'name', 'valuemap')
    search_labels = ('image__name', 'name')
    search_fields = ('image__name', 'name')
