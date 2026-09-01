from django.contrib import admin
from django.db import transaction

from .models import Profile, Note
from .models import Group, UserGroupBinding
from .models import Thumbnail, Token, TokenType

from .services.live import (
    broadcast_global_live_event,
)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'uid_number', 'can_createproject', 'can_createimage', 'can_createattachment', 'can_runjob', 'has_scratch')
    search_fields = ('user__username', )


def broadcast_notes_changed():
    broadcast_global_live_event(
        keys=["hub-notes"],
        payload={
            "model": "note-list",
            "reason": "notes.changed",
        },
    )

@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "expired",
        "is_public",
        "message",
    )

    def save_model(
        self,
        request,
        obj,
        form,
        change,
    ):
        super().save_model(
            request,
            obj,
            form,
            change,
        )

        transaction.on_commit(
            broadcast_notes_changed
        )

    def delete_model(
        self,
        request,
        obj,
    ):
        super().delete_model(
            request,
            obj,
        )

        transaction.on_commit(
            broadcast_notes_changed
        )

    def delete_queryset(
        self,
        request,
        queryset,
    ):
        super().delete_queryset(
            request,
            queryset,
        )

        transaction.on_commit(
            broadcast_notes_changed
        )
        

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

@admin.register(TokenType)
class TokenTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')

@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'value')
    
    
# @admin.register(Service)
# class ServiceAdmin(admin.ModelAdmin):
#     list_display = ('id', 'service_type')


