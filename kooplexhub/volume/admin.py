from django.contrib import admin

from .models import Volume

@admin.register(Volume)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'claim', 'subPath', 'is_present', 'description')
    search_fields = ('name', 'claim', 'description')
