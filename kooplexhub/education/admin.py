from django.contrib import admin

from .models import Course, CourseCode
from .models import UserCourseBinding, UserCourseCodeBinding
from .models import CourseContainerBinding
from .models import Assignment, UserAssignmentBinding
from .models import CourseGroup, UserCourseGroupBinding
from .models import UserCourseGroupBinding


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    def teachers(self, instance):
        return list(map(lambda x: x.user, UserCourseBinding.objects.filter(course = instance, is_teacher = True)))
    list_display = ('id', 'name', 'cleanname', 'folder', 'description', 'image', 'teacher_can_delete_foreign_assignment', 'teachers')
    search_fields = ('name', 'description')


@admin.register(CourseCode)
class UserProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'courseid', 'course')
    search_fields = ('courseid', )


@admin.register(UserCourseBinding)
class UserCourseBindingAdmin(admin.ModelAdmin):
    def course_name(self, instance):
        return instance.course.name
    def user_first_name(self, instance):
        return instance.user.first_name
    def user_last_name(self, instance):
        return instance.user.last_name
    def user_username(self, instance):
        return instance.user.username
    list_display = ('id', 'course_name', 'is_teacher', 'user_first_name', 'user_last_name', 'user_username')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'course__name')


@admin.register(UserCourseCodeBinding)
class UserCourseCodeBindingAdmin(admin.ModelAdmin):
    def coursecode_course_name(self, instance):
        return instance.coursecode.course.name
    list_display = ('id', 'user', 'coursecode', 'coursecode_course_name')


@admin.register(CourseContainerBinding)
class CourseContainerBindingAdmin(admin.ModelAdmin):
    def container_user(self, instance):
        return instance.container.user
    def container_state(self, instance):
        return instance.container.state
    list_display = ('id', 'course', 'container', 'container_user', 'container_state')
    search_fields = ('course__name', 'container__user__first_name', 'container__user__last_name')


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'name', 'folder', 'creator', 'description', 'created_at', 'filename', 'valid_from', 'expires_at', 'remove_collected', 'max_size')
    search_fields = ('name', 'creator__first_name', 'creator__last_name', 'course__name')


@admin.register(UserAssignmentBinding)
class UserAssignmentAdmin(admin.ModelAdmin):
    def assignment_course_name(self, instance):
        return instance.assignment.course.name
    def assignment_name(self, instance):
        return instance.assignment.name
    list_display = ('id', 'assignment_course_name', 'assignment_name', 'user', 'state', 'submit_count', 'score', 'feedback_text')
    search_fields = ('assignment__name', 'user__first_name', 'user__last_name')


@admin.register(CourseGroup)
class CourseGroupAdmin(admin.ModelAdmin):
    def course_name(self, instance):
        return instance.course.name
    list_display = ('id', 'course_name', 'name', 'description')
    search_fields = ('course__name', 'name')


@admin.register(UserCourseGroupBinding)
class UserCourseGroupBindingAdmin(admin.ModelAdmin):
    def course_name(self, instance):
        return instance.usercoursebinding.course.name
    def group_name(self, instance):
        return instance.group.name
    def username(self, instance):
        u = instance.usercoursebinding.user
        return f'{u.first_name} {u.last_name} ({u.username})'
    list_display = ('id', 'course_name', 'group_name', 'username')
    search_fields = ('usercoursebinding__course__name', 'usercoursebinding__user__username', 'usercoursebinding__user__first_name', 'usercoursebinding__user__last_name')
