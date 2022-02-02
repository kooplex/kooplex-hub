from django.contrib import admin

from .models import FilesystemTask
from .models import Profile, Note
from .models import Group, UserGroupBinding

@admin.register(FilesystemTask)
class FilesystemTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'launched_at', 'task', 'folder', 'tarbal', 'users_ro', 'users_rw', 'groups_ro', 'groups_rw', 'create_folder', 'remove_folder', 'stop_at', 'error')


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'user', 'userid', 'is_teacher', 'is_student', 'can_createproject', 'can_createimage', 'can_createattachment')
    search_fields = ('user__username', )


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'expired', 'is_public', 'message')


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'groupid', 'grouptype')


@admin.register(UserGroupBinding)
class UserGroupBindingAdmin(admin.ModelAdmin):
    def name(_, instance):
        return "{} {}".format(instance.user.first_name, instance.user.last_name)
    list_display = ('id', 'name', 'user', 'group')

