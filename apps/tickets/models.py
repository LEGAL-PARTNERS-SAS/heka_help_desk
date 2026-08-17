"""
apps/tickets/models.py
Modelos: TicketCategory, Ticket, TicketComment, TicketAttachment, TicketStatusHistory.
"""

from django.db import models
from django.conf import settings
from apps.core.models import Area


class TicketStatusChoices(models.TextChoices):
    ABIERTO     = 'abierto',     'Abierto'
    EN_PROCESO  = 'en_proceso',  'En Proceso'
    PENDIENTE   = 'pendiente',   'Pendiente'
    EN_ESPERA   = 'en_espera',   'En Espera'
    ESCALADO    = 'escalado',    'Escalado'
    RESUELTO    = 'resuelto',    'Resuelto'
    CERRADO     = 'cerrado',     'Cerrado'


class TicketPriorityChoices(models.TextChoices):
    BAJA    = 'baja',    'Baja'
    MEDIA   = 'media',   'Media'
    ALTA    = 'alta',    'Alta'
    CRITICA = 'critica', 'Crítica'


# ─── Categoría ────────────────────────────────────────────────────────────────
class TicketCategory(models.Model):
    categoryId   = models.AutoField(primary_key=True, db_column='category_id')
    categoryName = models.CharField(max_length=150, db_column='category_name')
    area         = models.ForeignKey(
                       Area, on_delete=models.CASCADE,
                       db_column='area_id', related_name='ticketCategories'
                   )

    class Meta:
        managed = False
        db_table = 'ticket_categories'
        verbose_name = 'Categoría de Ticket'
        verbose_name_plural = 'Categorías de Tickets'
        ordering = ['categoryName']

    def __str__(self):
        return f'{self.categoryName} ({self.area})'


# ─── Ticket ───────────────────────────────────────────────────────────────────
class Ticket(models.Model):
    ticketId     = models.AutoField(primary_key=True, db_column='ticket_id')
    ticketNumber = models.CharField(max_length=20, unique=True, db_column='ticket_number')
    title        = models.CharField(max_length=200, db_column='title')
    description  = models.TextField(db_column='description')
    status       = models.CharField(
                       max_length=20,
                       choices=TicketStatusChoices.choices,
                       default=TicketStatusChoices.ABIERTO,
                       db_column='status'
                   )
    priority     = models.CharField(
                       max_length=10,
                       choices=TicketPriorityChoices.choices,
                       default=TicketPriorityChoices.MEDIA,
                       db_column='priority'
                   )
    createdBy    = models.ForeignKey(
                       settings.AUTH_USER_MODEL, on_delete=models.RESTRICT,
                       db_column='created_by', related_name='ticketsCreated'
                   )
    assignedTo   = models.ForeignKey(
                       settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                       null=True, blank=True,
                       db_column='assigned_to', related_name='ticketsAssigned'
                   )
    category     = models.ForeignKey(
                       TicketCategory, on_delete=models.RESTRICT,
                       db_column='category_id', related_name='tickets'
                   )
    area         = models.ForeignKey(
                       Area, on_delete=models.RESTRICT,
                       db_column='area_id', related_name='tickets'
                   )
    createdAt    = models.DateTimeField(auto_now_add=True, db_column='created_at')
    closedAt     = models.DateTimeField(null=True, blank=True, db_column='closed_at')

    class Meta:
        managed = False
        db_table = 'tickets'
        verbose_name = 'Ticket'
        verbose_name_plural = 'Tickets'
        ordering = ['-createdAt']
        indexes = [
            models.Index(fields=['status'],     name='idx_tickets_status'),
            models.Index(fields=['area'],       name='idx_tickets_area'),
            models.Index(fields=['assignedTo'], name='idx_tickets_assigned'),
        ]

    def __str__(self):
        return f'[{self.ticketNumber}] {self.title}'

    def close(self, commit=True):
        from django.utils import timezone
        self.status   = TicketStatusChoices.CERRADO
        self.closedAt = timezone.now()
        if commit:
            self.save(update_fields=['status', 'closedAt'])

    @property
    def resolution_time(self):
        """Retorna el tiempo de resolución como string legible si el ticket está cerrado o resuelto."""
        if not self.closedAt or not self.createdAt:
            return None
        delta = self.closedAt - self.createdAt
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            return None
        days    = delta.days
        hours   = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        parts = []
        if days:
            parts.append(f'{days}d')
        if hours:
            parts.append(f'{hours}h')
        if minutes or not parts:
            parts.append(f'{minutes}min')
        return ' '.join(parts)


# ─── Comentario ───────────────────────────────────────────────────────────────
class TicketComment(models.Model):
    commentId = models.AutoField(primary_key=True, db_column='comment_id')
    ticket    = models.ForeignKey(
                    Ticket, on_delete=models.CASCADE,
                    db_column='ticket_id', related_name='comments'
                )
    user      = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.RESTRICT,
                    db_column='user_id', related_name='ticketComments'
                )
    comment   = models.TextField(db_column='comment')
    createdAt = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        managed = False
        db_table = 'ticket_comments'
        verbose_name = 'Comentario'
        verbose_name_plural = 'Comentarios'
        ordering = ['createdAt']
        indexes = [
            models.Index(fields=['ticket'], name='idx_comments_ticket'),
        ]

    def __str__(self):
        return f'Comentario de {self.user} en {self.ticket}'


# ─── Adjunto ──────────────────────────────────────────────────────────────────
class TicketAttachment(models.Model):
    attachmentId = models.AutoField(primary_key=True, db_column='attachment_id')
    ticket       = models.ForeignKey(
                       Ticket, on_delete=models.CASCADE,
                       db_column='ticket_id', related_name='attachments'
                   )
    fileName     = models.CharField(max_length=255, db_column='file_name')
    filePath     = models.TextField(db_column='file_path')
    uploadedBy   = models.ForeignKey(
                       settings.AUTH_USER_MODEL, on_delete=models.RESTRICT,
                       db_column='uploaded_by', related_name='ticketAttachments'
                   )
    uploadedAt   = models.DateTimeField(auto_now_add=True, db_column='uploaded_at')

    class Meta:
        managed = False
        db_table = 'ticket_attachments'
        verbose_name = 'Adjunto'
        verbose_name_plural = 'Adjuntos'

    def __str__(self):
        return self.fileName


# ─── Historial de estado ──────────────────────────────────────────────────────
class TicketStatusHistory(models.Model):
    historyId = models.AutoField(primary_key=True, db_column='history_id')
    ticket    = models.ForeignKey(
                    Ticket, on_delete=models.CASCADE,
                    db_column='ticket_id', related_name='statusHistory'
                )
    oldStatus = models.CharField(
                    max_length=20, null=True, blank=True,
                    choices=TicketStatusChoices.choices,
                    db_column='old_status'
                )
    newStatus = models.CharField(
                    max_length=20,
                    choices=TicketStatusChoices.choices,
                    db_column='new_status'
                )
    changedBy = models.ForeignKey(
                    settings.AUTH_USER_MODEL, on_delete=models.RESTRICT,
                    db_column='changed_by', related_name='statusChanges'
                )
    changedAt = models.DateTimeField(auto_now_add=True, db_column='changed_at')

    class Meta:
        managed = False
        db_table = 'ticket_status_history'
        verbose_name = 'Historial de Estado'
        verbose_name_plural = 'Historial de Estados'
        ordering = ['-changedAt']

    def __str__(self):
        return f'{self.ticket} | {self.oldStatus} → {self.newStatus}'
