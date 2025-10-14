from django.contrib import admin

# Register your models here.

from .models.canvas import *


@admin.register(CanvasCourse)
class CanvasCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'course', 'creator')
    search_labels = ('name', 'course',)
    search_fields = ('name', 'course',)

