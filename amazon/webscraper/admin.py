from django.contrib import admin

from .models import AsinsMonitoring, AdvertisingMonitoring


@admin.register(AsinsMonitoring)
class AsinsMonitoringAdmin(admin.ModelAdmin):
    pass


@admin.register(AdvertisingMonitoring)
class AdvertisingMonitoringAdmin(admin.ModelAdmin):
    pass

