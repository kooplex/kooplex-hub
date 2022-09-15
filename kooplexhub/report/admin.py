from django.contrib import admin

# Register your models here.
from .models import Report, ReportType, ReportContainerBinding

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    def report_creator(self, instance):
        return instance.creator
    list_display = ('id', 'report_creator', 'name', 'project', 'folder', 'scope', 'index', 'image')

@admin.register(ReportContainerBinding)
class ReportContainerBindingAdmin(admin.ModelAdmin):
    def report_creator(self, instance):
        return instance.report.creator
    list_display = ('id', 'report', 'container', 'report_creator')

@admin.register(ReportType)
class ReportTypengAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'url_tag')
