import logging

from django.contrib import messages
from django.conf.urls import url
from django.shortcuts import redirect
from django.contrib import admin

from kooplex.hub.models import *
from kooplex.logic.project import mark_containers_remove

logger = logging.getLogger(__name__)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'first_name', 'last_name', 'uid', 'gitlab_id', 'n_projects', 'n_reports')
    #fieldsets = ( (None, { 'fields': (( 'first_name', 'last_name'), ('username', 'email'), 'bio', 'user_permissions') }),    )
    fieldsets = ( (None, { 'fields': (( 'first_name', 'last_name'), ('username', 'email'), 'bio' ) }),    )
    actions = ['reset_password', 'remove_users' ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def changelist_view(self, request, extra_context = None):
        extra_context = extra_context or {}
        extra_context['messages'] = messages.get_messages(request)
        return super(UserAdmin, self).changelist_view(request, extra_context)

    def reset_password(self, request, queryset):
        msg = ""
        for user in queryset:
            user.generatenewpassword()
            msg += "%s, " % user.username
            logger.debug("reset_password: %s" % user)
        messages.success(request, "Password reseted for: %s" % msg)
    reset_password.short_description = 'Reset password'

    def remove_users(self, request, queryset):
        msg = ""
        oops = ""
        for user in queryset:
            try:
                user.remove()
                super().delete_model(request, user)
                msg += "%s, " % user
                logger.info("removed user: %s" % user)
            except Exception as e:
                logger.error("remove_user: %s -- %s" % (user, e))
                oops += "%s (%s), " % (user, e)
        if len(msg):
            messages.success(request, "Deleted: %s" % msg)
        if len(oops):
            messages.warning(request, "Ooopsed: %s" % oops)
    remove_users.short_description = 'Delete users in a neat way'

    def save_model(self, request, user, form, changed):
        try:
            user_old = User.objects.get(username = user.username)
            if user_old.email != user.email:
                # user.changeemail()  #TODO: if e-mail may change then gitlab user details have to be updated accordingly
                raise NotImplementedError
        except User.DoesNotExist:
            user.create()
            logger.info("user created: %s" % s)
        super().save_model(request, user, form, changed)

    def delete_model(self, request, user):
        user.remove()
        logger.info("removed user: %s" % user)
        super().delete_model(request, user)

def stop_containers(klass, request, queryset):
    from kooplex.logic.spawner import stop_container
    msg = ""
    oops = ""
    for container in queryset:
        try:
            stop_container(container)
            logger.info("removed container: %s" % container)
            msg += "%s, " % container
        except Exception as e:
            logger.error("cannot remove container: %s -- %s" % (container, e))
            oops += "%s, " % container
    if len(msg):
        messages.success(request, "stopped: %s" % msg)
    if len(oops):
        messages.warning(request, "oopses: %s" % oops)
stop_containers.short_description = 'Stop selected containers'

@admin.register(ProjectContainer)
class ProjectContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'project', 'uptime', 'url')
    actions = [ stop_containers, ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@admin.register(DashboardContainer)
class DashboardContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'report', 'uptime', 'url')
    actions = [ stop_containers, ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


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
    list_display = ('id', 'project', 'volume')
    actions = [ 'delete_vpb', ]

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def save_model(self, request, vpb, form, changed):
        try:
            VolumeProjectBinding.objects.get(project = vpb.project, volume = vpb.volume)
            messages.error(request, "Not saving %s, because that entry already exists" % vpb)
            logger.debug("not saving volume project binding to avoid duplication: %s" % vpb)
        except VolumeProjectBinding.DoesNotExist:
            n_mark, n_remove = mark_containers_remove(vpb.project)
            messages.success(request, "%d containers removed and %d containers marked to be removed" % (n_remove, n_mark))
            super().save_model(request, vpb, form, changed)
            logger.debug("saved volume project binding: %s, %d containers removed, %d containers marked to be removed" % (vpb, n_remove, n_mark))

    def delete_model(self, request, vpb):
        n_mark, n_remove = mark_containers_remove(vpb.project)
        messages.success(request, "# containers removed: %d and marked to be removed %d" % (n_remove, n_mark))
        super().delete_model(request, vpb)
        logger.debug("removed volume project binding: %s, %d containers removed, %d containers marked to be removed" % (vpb, n_remove, n_mark))

    def delete_vpb(self, request, queryset):
        msg = ""
        for vpb in queryset:
            self.delete_model(request, vpb)
    delete_vpb.short_description = 'Delete volume project bindings'

#def admin_main(request):
#   pass

def refreshimages(request):
#FIXME: authorize
    refresh_images()
    refresh_volumes()
    return redirect('/admin')

def initmodel(request):
#FIXME: authorize
#    init_containertypes()
    init_scopetypes()
    return redirect('/admin')

urlpatterns = [
    url(r'^refreshimages', refreshimages, name = 'refresh-images'),
    url(r'^initmodel', initmodel, name = 'init-model'),
]

