import logging

from django.contrib import admin

from django.conf.urls import url, include
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from hub.models import *

logger = logging.getLogger(__name__)


@login_required
def init_images(request):
    store_images()
    return redirect('indexpage')

@login_required
def init_volumes(request):
    store_volumes()
    return redirect('indexpage')

urlpatterns = [
    url(r'^init/images$', init_images, name = 'initimages'),
    url(r'^init/volumes$', init_volumes, name = 'initvolumes'),
]

#FIXME: shant be here
##def stop_containers(klass, request, queryset):
##    from kooplex.logic.spawner import stop_container
##    msg = ""
##    oops = ""
##    for container in queryset:
##        try:
##            stop_container(container)
##            logger.info("removed container: %s" % container)
##            msg += "%s, " % container
##        except Exception as e:
##            logger.error("cannot remove container: %s -- %s" % (container, e))
##            oops += "%s, " % container
#    if len(msg):
#        messages.success(request, "stopped: %s" % msg)
#    if len(oops):
#        messages.warning(request, "oopses: %s" % oops)
##stop_containers.short_description = 'Stop selected containers'

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'userid', 'groupid', 'location', 'bio', 'is_teacher', 'is_student', 'can_createproject')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image') 
#    actions = [ stop_containers, ]

@admin.register(UserProjectBinding)
class UserProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'project', 'role', 'is_hidden')
    search_fields = ('user__username','project__name')

@admin.register(GroupProjectBinding)
class GroupProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'group')

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'user', 'n_projects', 'marked_to_remove')

@admin.register(ProjectContainerBinding)
class ProjectContainerBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'container', 'project')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'courseid', 'safecourseid', 'description', 'project')

@admin.register(UserCourseBinding)
class UserCourseBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'flag', 'is_teacher', 'is_protected')
    search_fields = ('user__username','course__courseid')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'flag', 'name', 'safename', 'folder', 'creator', 'description', 'is_massassignment', 'created_at', 'valid_from', 'expires_at', 'can_studentsubmit')
    search_fields = ('creator__username', 'course__courseid' )

@admin.register(UserAssignmentBinding)
class UserAssignmentBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment_name', 'user', 'state', 'received_at', 'valid_from', 'expires_at', 'submitted_at', 'corrector', 'corrected_at', 'score', 'feedback_text')
    def assignment_name(self, instance):
        return instance.assignment.name
    search_fields = ('user__username', 'assignment__name' )

@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'displayname', 'description', 'volumetype')

@admin.register(VolumeOwnerBinding)
class VolumeOwnerBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'volume', 'owner')

@admin.register(ExtraFields)
class ExtraFieldsAdmin(admin.ModelAdmin):
    list_display = ('id', 'volume', 'groupid', 'public', 'is_writable')

@admin.register(VolumeProjectBinding)
class VolumeProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'volume')
#    actions = [ 'delete_vpb', ]
#
#    def get_actions(self, request):
#        actions = super().get_actions(request)
#        if 'delete_selected' in actions:
#            del actions['delete_selected']
#        return actions
#
#    def save_model(self, request, vpb, form, changed):
#        try:
#            VolumeProjectBinding.objects.get(project = vpb.project, volume = vpb.volume)
#            messages.error(request, "Not saving %s, because that entry already exists" % vpb)
#            logger.debug("not saving volume project binding to avoid duplication: %s" % vpb)
#        except VolumeProjectBinding.DoesNotExist:
#            n_mark, n_remove = mark_containers_remove(vpb.project)
#            messages.success(request, "%d containers removed and %d containers marked to be removed" % (n_remove, n_mark))
#            super().save_model(request, vpb, form, changed)
#            logger.debug("saved volume project binding: %s, %d containers removed, %d containers marked to be removed" % (vpb, n_remove, n_mark))
#
#    def delete_model(self, request, vpb):
#        n_mark, n_remove = mark_containers_remove(vpb.project)
#        messages.success(request, "# containers removed: %d and marked to be removed %d" % (n_remove, n_mark))
#        super().delete_model(request, vpb)
#        logger.debug("removed volume project binding: %s, %d containers removed, %d containers marked to be removed" % (vpb, n_remove, n_mark))
#
#    def delete_vpb(self, request, queryset):
#        msg = ""
#        for vpb in queryset:
#            self.delete_model(request, vpb)
#    delete_vpb.short_description = 'Delete volume project bindings'
    
@admin.register(VolumeContainerBinding)
class VolumeContainerBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'container', 'project', 'volume' )

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'groupid', 'name', 'project', 'is_active')

@admin.register(UserGroupBinding)
class UserGroupBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'user')
