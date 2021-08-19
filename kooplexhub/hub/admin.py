from django.contrib import admin

from .models import Profile, Note

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'user', 'userid', 'is_teacher', 'is_student', 'can_createproject', 'can_createimage', 'can_createattachment')
    search_fields = ('user__username', )

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'expired', 'is_public', 'message')


