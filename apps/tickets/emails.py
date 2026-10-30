"""
apps/tickets/emails.py — correo HTML para los eventos de Tickets (ticket
nuevo, cambio de estado, asignación, comentario nuevo).

Hasta ahora el sistema solo creaba notificaciones internas (ver
apps/core/models.py::Notification) y nunca mandaba nada por correo, así
que a alguien que no tuviera la pestaña abierta se le podía pasar por
alto un ticket nuevo o una respuesta. Reutiliza la plantilla compartida
de apps/core/emails.py (la misma que ya usan horas, api-mensajeria,
reporte-cartera e inventario, ver memoria project_correos_heka_rediseno).

El envío nunca debe tumbar el flujo de un ticket si el correo falla,
mismo criterio que ya aplica _notificar_ticket() para las notificaciones
internas (`Notificaciones no bloquean el flujo principal`).
"""
import html as _html

from apps.core.emails import TEMAS, render_shell
from celery_tasks.tasks import sendHtmlMailTask

_TIPO_A_TEMA = {
    'ticket_nuevo':      'azul',
    'ticket_asignado':   'azul',
    'ticket_estado':     'azul',
    'ticket_comentario': 'azul',
    'ticket_cerrado':    'verde',
}


def enviar_notificacion_ticket(destinatarios, tipo: str, titulo: str, mensaje: str, ticket) -> None:
    """destinatarios: iterable de instancias de User (con .email)."""
    correos = [u.email for u in destinatarios if getattr(u, 'email', None)]
    if not correos:
        return

    tema = TEMAS[_TIPO_A_TEMA.get(tipo, 'azul')]
    cta_url = f'https://soporte.heka.com.ec/tickets/{ticket.ticketId}/'

    html_body = render_shell(
        eyebrow=f'Ticket {ticket.ticketNumber}',
        titulo=titulo,
        intro_html=_html.escape(mensaje),
        detalle=[
            ('Área', ticket.area.areaName),
            ('Estado', ticket.get_status_display()),
            ('Prioridad', ticket.get_priority_display()),
        ],
        cta_label='Ver ticket',
        cta_url=cta_url,
        app_nombre='Tickets',
        **tema,
    )

    asunto = f'[{ticket.ticketNumber}] {titulo}'
    for correo in correos:
        # Un correo por destinatario, pero despachado a Celery -- la vista
        # ya no espera a que termine cada conexion SMTP para responder.
        sendHtmlMailTask.delay(correo, asunto, html_body, mensaje)
