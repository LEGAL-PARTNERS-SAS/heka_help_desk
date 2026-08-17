from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Ticket, TicketStatusHistory


@receiver(pre_save, sender=Ticket)
def captureOldStatus(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._oldStatus = Ticket.objects.get(pk=instance.pk).status
        except Ticket.DoesNotExist:
            instance._oldStatus = None
    else:
        instance._oldStatus = None


@receiver(post_save, sender=Ticket)
def registerStatusChange(sender, instance, created, **kwargs):
    oldStatus = getattr(instance, '_oldStatus', None)
    changedBy = getattr(instance, '_changedBy', instance.createdBy)

    if created:
        TicketStatusHistory.objects.create(
            ticket=instance,
            oldStatus=None,
            newStatus=instance.status,
            changedBy=changedBy,
        )
    elif oldStatus and oldStatus != instance.status:
        TicketStatusHistory.objects.create(
            ticket=instance,
            oldStatus=oldStatus,
            newStatus=instance.status,
            changedBy=changedBy,
        )
