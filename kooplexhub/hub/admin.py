import logging

from django.contrib import admin

from django.conf.urls import url, include
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required

from hub.models import *

logger = logging.getLogger(__name__)

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'userid', 'groupid', 'location', 'bio', 'is_teacher', 'is_student', 'can_createproject')
    search_fields = ('user__username', )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    def project_creator(self, instance):
        return instance.creator
    list_display = ('id', 'name', 'image', 'project_creator') 

@admin.register(UserProjectBinding)
class UserProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'project', 'role', 'is_hidden')
    search_fields = ('user__username','project__name')

@admin.register(GroupProjectBinding)
class GroupProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'group')

@admin.register(Container)
class ContainerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'image', 'user', 'state', 'n_projects', 'marked_to_remove')

@admin.register(ContainerEnvironment)
class ContainerEnvironmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'container', 'name', 'value')

@admin.register(ProjectContainerBinding)
class ProjectContainerBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'container', 'project')

@admin.register(ReportContainerBinding)
class ReportContainerBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'container', 'report')

@admin.register(CourseCode)
class CourseCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'courseid', 'safecourseid', 'course')
    search_fields = ('courseid', )

@admin.register(CourseContainerBinding)
class CourseContainerBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'container', 'course')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'folder', 'description', 'image')

@admin.register(UserCourseCodeBinding)
class UserCourseCodeBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'coursecode', 'is_teacher', 'is_protected')
    search_fields = ('user__username', 'coursecode__courseid')

@admin.register(UserCourseBinding)
class UserCourseBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'is_teacher', 'is_protected')
    search_fields = ('user__username', 'course__name')

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'coursecode', 'name', 'safename', 'folder', 'creator', 'description', 'is_massassignment', 'remove_collected', 'created_at', 'valid_from', 'expires_at', 'can_studentsubmit')
    search_fields = ('creator__username', 'coursecode__courseid')

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
    list_display = ('id', 'container', 'volume' )

@admin.register(Image)
class ImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'groupid', 'name' )

@admin.register(UserGroupBinding)
class UserGroupBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'user')


@admin.register(VCRepository)
class VCRepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'backend_type', 'url', 'ssh_port')

@admin.register(VCToken)
class VCTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'username', 'repository', 'fn_rsa')

@admin.register(VCProject)
class VCProjectAdmin(admin.ModelAdmin):
    list_display = ('id', 'repo', 'project_name', 'project_id', 'project_description', 'project_created_at', 'project_updated_at', 'project_fullname', 'project_owner', 'project_ssh_url', 'last_seen', 'cloned', 'clone_folder')
    search_fields = ('project_name', 'project_owner', 'token__repository__url', )
    def repo(self, instance):
        return instance.token.repository.url

@admin.register(VCProjectProjectBinding)
class VCProjectProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'vcproject')


@admin.register(FSServer)
class FSServerAdmin(admin.ModelAdmin):
    list_display = ('id', 'backend_type', 'url')

@admin.register(FSToken)
class FSTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'syncserver')

@admin.register(FSLibrary)
class FSLibraryAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user', 'get_syncserver', 'library_name', 'library_id', 'sync_folder')
    search_fields = ('token__user__username', 'library_name')
    def get_user(self, obj):
        return obj.token.user.username
    get_user.short_description = 'Username'
    get_user.admin_order_field = 'token__user__username'
    def get_syncserver(self, obj):
        return obj.token.syncserver
    get_syncserver.short_description = 'Sync server'
    get_syncserver.admin_order_field = 'token__syncserver'

@admin.register(FSLibraryProjectBinding)
class FSLibraryProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'fslibrary')


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'creator', 'created_at', 'reporttype', 'index', 'image') 
