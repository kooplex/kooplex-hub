from django.contrib import admin

from .models import Profile, Note
from .models import Group, UserGroupBinding

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
    def username(instance): 
        return instance.username
    def groupname(instance):
        return instance.name
    list_display = ('id', 'username', 'groupname')

