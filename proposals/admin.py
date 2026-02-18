from django.contrib import admin
from .models import Service, TKPRecord


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_file', 'unit', 'order']
    list_editable = ['order']


@admin.register(TKPRecord)
class TKPRecordAdmin(admin.ModelAdmin):
    list_display = ['number', 'date', 'client', 'service', 'sum_total']
    list_filter = ['date', 'service']
    search_fields = ['number', 'client']
