from django.contrib import admin

from .models import *

@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ('id', 'folder', 'claim', 'subPath', 'is_present', 'description')
    search_fields = ('folder', 'claim', 'description')

@admin.register(VolumeContainerBinding)
class VolumeContainerBindingAdmin(admin.ModelAdmin):
    def container_username(self, instance):
        return instance.container.user.username
    list_display = ('id', 'volume', 'container', 'container_username')

@admin.register(UserVolumeBinding)
class UserVolumeBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'volume', 'role')
    search_fields = ('user__username','volume__name')
