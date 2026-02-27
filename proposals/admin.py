from django.contrib import admin
from .models import Counterparty, Region, RegionServicePrice, Service, TKPRecord


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name']


@admin.register(RegionServicePrice)
class RegionServicePriceAdmin(admin.ModelAdmin):
    list_display = ['region', 'service', 'unit_price']
    list_filter = ['region', 'service']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_file', 'unit_type', 'order']
    list_editable = ['order']


@admin.register(TKPRecord)
class TKPRecordAdmin(admin.ModelAdmin):
    list_display = ['number', 'date', 'client', 'service', 'sum_total']
    list_filter = ['date', 'service']
    search_fields = ['number', 'client']


@admin.register(Counterparty)
class CounterpartyAdmin(admin.ModelAdmin):
    list_display = ['name', 'inn', 'director', 'created_at']
    search_fields = ['name', 'inn', 'director']
