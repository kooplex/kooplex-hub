from django.contrib import admin

# Register your models here.
from .models import Report, ReportType, ReportContainerBinding, ReportTag

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    def report_creator(self, instance):
        return instance.creator
    list_display = ('id', 'report_creator', 'name', 'project', 'folder', 'scope', 'indexfile', 'image')
    search_labels = ('name', 'report_creator__username', 'folder', 'image')
    search_fields = ('name', 'report_creator__username', 'folder', 'image')

@admin.register(ReportContainerBinding)
class ReportContainerBindingAdmin(admin.ModelAdmin):
    def report_creator(self, instance):
        return instance.report.creator
    list_display = ('id', 'report', 'container', 'report_creator')

@admin.register(ReportType)
class ReportTypengAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(ReportTag)
class ReportTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

