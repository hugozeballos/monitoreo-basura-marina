from django.contrib import admin
from .models import monitoreo, usuarios
# Register your models here.

class monitoreoAdmin(admin.ModelAdmin):
    readonly_fields=("created", "updated")

admin.site.register(monitoreo, monitoreoAdmin)