from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('action', 'user', 'tableName', 'recordId', 'ipAddress', 'createdAt')
    list_filter   = ('tableName',)
    search_fields = ('action', 'user__email')
    readonly_fields = ('logId', 'createdAt')
