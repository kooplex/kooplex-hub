from django.contrib import admin

# Register your models here.

from .models.canvas import *


@admin.register(CanvasCourse)
class CanvasCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name',  'course')
    search_labels = ('name', 'course')
    search_fields = ('name', 'course')

@admin.register(Canvas)
class CanvasAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', )
    search_labels = ('name', 'user')
    search_fields = ('name', 'user')
