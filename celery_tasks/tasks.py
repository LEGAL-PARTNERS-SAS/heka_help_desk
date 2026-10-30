from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sendHtmlMailTask(self, to, subject, html_body, plain_fallback=''):
    """Despacha un correo HTML ya armado (ver apps/core/emails.py::
    send_html_mail) fuera del hilo de la petición. Antes cada destinatario
    de una notificación de ticket se mandaba en serie, con una conexión
    SMTP nueva por persona, bloqueando la respuesta del navegador hasta
    que el último correo salía — con un área de 4-5 agentes, varios
    segundos por cada ticket creado/actualizado/comentado."""
    from apps.core.emails import send_html_mail

    ok = send_html_mail(to=to, subject=subject, html_body=html_body, plain_fallback=plain_fallback)
    if not ok:
        raise self.retry(exc=RuntimeError(f'send_html_mail devolvio False para {to}'))
    return {'status': 'ok', 'to': to}


@shared_task(bind=True, max_retries=3)
def sendTicketNotificationEmail(self, recipientEmail, ticketNumber, subject, message):
    try:
        send_mail(
            subject=f'[Ticket {ticketNumber}] {subject}',
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[recipientEmail],
            fail_silently=False,
        )
        logger.info(f'Email enviado a {recipientEmail} para ticket {ticketNumber}')
        return {'status': 'ok', 'recipient': recipientEmail}
    except Exception as exc:
        logger.error(f'Error al enviar email: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task
def closeInactiveTickets():
    from django.utils import timezone
    from datetime import timedelta
    from apps.tickets.models import Ticket, TicketStatusChoices

    cutoffDate = timezone.now() - timedelta(days=30)
    tickets    = Ticket.objects.filter(status=TicketStatusChoices.ABIERTO, createdAt__lte=cutoffDate)
    count      = tickets.count()
    for ticket in tickets:
        ticket.close(changedBy=None)
    logger.info(f'Tickets cerrados automaticamente: {count}')
    return {'ticketsClosed': count}
