from django.contrib import admin

from .models import Profile, Note
from .models import Group, UserGroupBinding
from .models import Thumbnail


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'user', 'userid', 'is_teacher', 'is_student', 'can_createproject', 'can_createimage', 'can_createattachment', 'can_runjob', 'has_scratch')
    search_fields = ('user__username', )


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'expired', 'is_public', 'message')


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'groupid', 'grouptype')
    search_fields = ('name', 'grouptype')


@admin.register(UserGroupBinding)
class UserGroupBindingAdmin(admin.ModelAdmin):
    def name(_, instance):
        return "{} {}".format(instance.user.first_name, instance.user.last_name)
    list_display = ('id', 'name', 'user', 'group')
    search_fields = ('group__name', 'user__username', 'user__last_name')


@admin.register(Thumbnail)
class ThumbnailAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'to_html')

