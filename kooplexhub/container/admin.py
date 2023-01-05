from django.contrib import admin

from .models import *

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'present', 'name', 'imagetype', 'description', 'require_home', 'mount_project', 'mount_report', 'access_kubeapi')

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'suffix', 'label', 'friendly_name', 'image', 'state', 'launched_at', 'restart_reasons')
    search_labels = ('name', 'user__username')

@admin.register(Proxy)
class ProxyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'default', 'token_as_argument', 'path', 'path_open', 'port')

@admin.register(EnvVarMapping)
class EnvVarMappingAdmin(admin.ModelAdmin):
    list_display = ('id', 'image', 'name', 'valuemap')

@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator', 'name', 'folder', 'description')

@admin.register(AttachmentContainerBinding)
class AttachmentContainerBindingAdmin(admin.ModelAdmin):
    def attachment_creator(self, instance):
        return instance.attachment.creator.username
    def attachment_name(self, instance):
        return instance.attachment.name
    list_display = ('id', 'attachment_name', 'attachment_creator', 'container')

@admin.register(AttachmentImageBinding)
class AttachmentImageBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'attachment', 'image')


