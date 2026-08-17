"""
apps/core/models.py
Modelos compartidos: Area y Role.
"""

from django.db import models


class Area(models.Model):
    areaId   = models.AutoField(primary_key=True, db_column='area_id')
    areaName = models.CharField(max_length=100, unique=True, db_column='area_name')

    class Meta:
        managed = False
        db_table = 'areas'
        verbose_name = 'Área'
        verbose_name_plural = 'Áreas'
        ordering = ['areaName']

    def __str__(self):
        return self.areaName


class Role(models.Model):
    roleId      = models.AutoField(primary_key=True, db_column='role_id')
    roleName    = models.CharField(max_length=100, unique=True, db_column='role_name')
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['roleName']

    def __str__(self):
        return self.roleName


class Notification(models.Model):
    TIPO_CHOICES = [
        ('ticket_nuevo',      '🎫 Ticket nuevo'),
        ('ticket_asignado',   '👤 Ticket asignado'),
        ('ticket_estado',     '🔄 Cambio de estado'),
        ('ticket_comentario', '💬 Nuevo comentario'),
        ('ticket_cerrado',    '✅ Ticket cerrado'),
    ]

    notifId      = models.AutoField(primary_key=True, db_column='notif_id')
    destinatario = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        db_column='user_id', related_name='notificaciones'
    )
    tipo      = models.CharField(max_length=30, choices=TIPO_CHOICES, db_column='tipo')
    titulo    = models.CharField(max_length=200, db_column='titulo')
    mensaje   = models.TextField(db_column='mensaje')
    leida     = models.BooleanField(default=False, db_column='leida')
    ticket_id = models.IntegerField(null=True, blank=True, db_column='ticket_id')
    createdAt = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        managed  = False   # la tabla se crea con el SQL adjunto
        db_table = 'notifications'
        ordering = ['-createdAt']

    def __str__(self):
        return f'[{self.tipo}] → {self.destinatario} — {self.titulo}'

    @classmethod
    def crear(cls, destinatario, tipo, titulo, mensaje, ticket=None):
        return cls.objects.create(
            destinatario=destinatario, tipo=tipo,
            titulo=titulo, mensaje=mensaje,
            ticket_id=ticket.pk if ticket else None,
        )

    @classmethod
    def crear_para_area(cls, area_name, tipo, titulo, mensaje, ticket=None, excluir_user=None):
        from apps.users.models import User
        from apps.core.permissions import AGENT_ROLE_MAP, AREA_ADMIN_ROLE_MAP

        roles_del_area = [
            rol for rol, areas in {**AGENT_ROLE_MAP, **AREA_ADMIN_ROLE_MAP}.items()
            if area_name in areas
        ]
        destinatarios = User.objects.filter(role__roleName__in=roles_del_area, status='activo')
        if excluir_user:
            destinatarios = destinatarios.exclude(pk=excluir_user.pk)

        cls.objects.bulk_create([
            cls(destinatario=u, tipo=tipo, titulo=titulo, mensaje=mensaje,
                ticket_id=ticket.pk if ticket else None)
            for u in destinatarios
        ])
