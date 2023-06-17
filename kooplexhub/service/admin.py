from django.contrib import admin

# Register your models here.
from .models import *

@admin.register(SeafileService)
class SeafileServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'kubernetes_secret_name')

@admin.register(UserSeafileServiceBinding)
class UserSeafileServiceBindingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'service', 'token')
