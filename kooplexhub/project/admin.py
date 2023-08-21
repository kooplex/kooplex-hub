from django.contrib import admin

from .models import Project
from .models import UserProjectBinding
from .models import ProjectContainerBinding

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    def project_creator(self, instance):
        return instance.creator
    def project_Nusers(self, instance):
        return len(instance.userprojectbindings)
    list_display = ('id', 'name', 'subpath', 'project_creator', 'scope', 'project_Nusers')
    search_labels = ('name', 'project_creator__username')
    search_fields = ('name', 'project_creator__username')

@admin.register(UserProjectBinding)
class UserProjectBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'project', 'role', 'is_hidden')
    search_fields = ('user__username','project__name')

@admin.register(ProjectContainerBinding)
class ProjectContainerBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'container')


