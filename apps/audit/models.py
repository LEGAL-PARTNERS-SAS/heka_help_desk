"""
apps/audit/models.py
Modelo de auditoría para registrar acciones del sistema.
"""

from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    logId     = models.AutoField(primary_key=True, db_column='log_id')
    user      = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                    null=True, blank=True,
                    db_column='user_id', related_name='auditLogs'
                )
    action    = models.CharField(max_length=200, db_column='action')
    tableName = models.CharField(max_length=100, null=True, blank=True, db_column='table_name')
    recordId  = models.IntegerField(null=True, blank=True, db_column='record_id')
    ipAddress = models.GenericIPAddressField(null=True, blank=True, db_column='ip_address')
    createdAt = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        managed = False
        db_table = 'audit_logs'
        verbose_name = 'Log de Auditoría'
        verbose_name_plural = 'Logs de Auditoría'
        ordering = ['-createdAt']
        indexes = [
            models.Index(fields=['user'], name='idx_audit_user'),
        ]

    def __str__(self):
        return f'[{self.createdAt:%Y-%m-%d %H:%M}] {self.action} por {self.user}'

    @classmethod
    def registrar(cls, user, action, tableName=None, recordId=None, ipAddress=None):
        """Helper para registrar una acción de forma rápida."""
        return cls.objects.create(
            user=user,
            action=action,
            tableName=tableName,
            recordId=recordId,
            ipAddress=ipAddress,
        )
