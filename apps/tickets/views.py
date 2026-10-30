"""
apps/tickets/views.py — con notificaciones, filtros y validación cédula
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Ticket, TicketCategory, TicketComment, TicketStatusHistory, TicketStatusChoices, TicketPriorityChoices
from apps.core.models import Area
from apps.core.permissions import (
    is_superadmin, is_area_admin, is_agent,
    get_allowed_area_names, can_assign_tickets, get_assignable_agents,
)

CERRADOS = (TicketStatusChoices.RESUELTO, TicketStatusChoices.CERRADO)
SLA_VENCIDO_HORAS = 48


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _tickets_for_user(user):
    if is_superadmin(user):
        return Ticket.objects.all().select_related('area', 'category', 'createdBy', 'assignedTo')
    if is_area_admin(user) or is_agent(user):
        allowed = get_allowed_area_names(user)
        return (
            Ticket.objects
            .filter(area__areaName__in=allowed)
            .select_related('area', 'category', 'createdBy', 'assignedTo')
        )
    return Ticket.objects.filter(createdBy=user).select_related('area', 'category', 'assignedTo')


def _can_access_ticket(user, ticket):
    if is_superadmin(user):
        return True
    if is_area_admin(user) or is_agent(user):
        return ticket.area.areaName in get_allowed_area_names(user)
    return ticket.createdBy == user


def _can_manage_ticket(user, ticket):
    if is_superadmin(user):
        return True
    if is_area_admin(user) or is_agent(user):
        return ticket.area.areaName in get_allowed_area_names(user)
    return False


def _agentes_asignables_para(ticket, user):
    """agentes (queryset), puede_asignar (bool) para el ticket dado, con el
    mismo criterio que ya usaba ticketUpdateView -- reusado ahora tambien
    por ticketDetailView para el cambio de estado/asignacion en linea."""
    puede_asignar = can_assign_tickets(user)
    if not puede_asignar:
        return None, False

    agentes = get_assignable_agents(ticket.area.areaName, user)
    if is_area_admin(user) or is_superadmin(user):
        from apps.users.models import User as UserModel
        admin_qs = UserModel.objects.filter(pk=user.pk)
        agentes = (agentes | admin_qs).distinct()
    return agentes, puede_asignar


# Verde → amarillo → naranja → rojo: la escala de "mapa de calor" de toda la
# vida (semáforo de severidad), no los tonos de marca -- a propósito, para
# que 0 tickets se lea como "tranquilo" y el máximo como "sobrecargado".
_ESCALA_CALOR = [
    (0.00, (34, 197, 94)),    # verde
    (0.33, (250, 204, 21)),   # amarillo
    (0.66, (249, 115, 22)),   # naranja
    (1.00, (239, 68, 68)),    # rojo
]


def _color_mapa_calor(ratio: float) -> str:
    ratio = max(0.0, min(1.0, ratio))
    for (r0, c0), (r1, c1) in zip(_ESCALA_CALOR, _ESCALA_CALOR[1:]):
        if ratio <= r1:
            t = (ratio - r0) / (r1 - r0) if r1 > r0 else 0
            rgb = tuple(round(c0[i] + (c1[i] - c0[i]) * t) for i in range(3))
            return f'rgb({rgb[0]},{rgb[1]},{rgb[2]})'
    return f'rgb({_ESCALA_CALOR[-1][1][0]},{_ESCALA_CALOR[-1][1][1]},{_ESCALA_CALOR[-1][1][2]})'


def _notificar_ticket(ticket, tipo, titulo, mensaje, actor):
    """Crea notificaciones internas para el área del ticket y, con los
    mismos destinatarios, manda el correo (ver apps/tickets/emails.py —
    antes esta función solo dejaba la notificación en campanita, y a quien
    no tuviera la pestaña abierta se le podía pasar por alto un ticket
    nuevo o una respuesta)."""
    destinatarios = []
    try:
        from apps.core.models import Notification
        destinatarios += Notification.crear_para_area(
            area_name=ticket.area.areaName,
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            ticket=ticket,
            excluir_user=actor,
        )
        # También notificar al creador si es usuario final y no es el actor
        if ticket.createdBy != actor and not is_area_admin(ticket.createdBy) and not is_agent(ticket.createdBy):
            Notification.crear(
                destinatario=ticket.createdBy,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                ticket=ticket,
            )
            destinatarios.append(ticket.createdBy)
        # Notificar al agente asignado si existe y no es el actor
        if ticket.assignedTo and ticket.assignedTo != actor:
            Notification.crear(
                destinatario=ticket.assignedTo,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                ticket=ticket,
            )
            destinatarios.append(ticket.assignedTo)
    except Exception:
        pass  # Notificaciones no bloquean el flujo principal

    try:
        from apps.tickets.emails import enviar_notificacion_ticket
        vistos = set()
        unicos = [u for u in destinatarios if not (u.pk in vistos or vistos.add(u.pk))]
        enviar_notificacion_ticket(unicos, tipo, titulo, mensaje, ticket)
    except Exception:
        pass  # El correo tampoco debe tumbar el flujo principal


# ─── Vistas ───────────────────────────────────────────────────────────────────

@login_required
def ticketListView(request):
    base_qs = _tickets_for_user(request.user).select_related('area', 'createdBy', 'assignedTo')

    status_filter   = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    area_filter     = request.GET.get('area', '')
    q               = request.GET.get('q', '').strip()
    vista           = request.GET.get('vista', '')   # chip rápido: vencidos / criticos

    tickets = base_qs.order_by('-createdAt')
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if area_filter:
        tickets = tickets.filter(area__areaId=area_filter)
    if q:
        tickets = tickets.filter(
            Q(title__icontains=q) | Q(ticketNumber__icontains=q) |
            Q(createdBy__name__icontains=q) | Q(createdBy__lastname__icontains=q)
        )

    ahora = timezone.now()
    corte_vencido = ahora - timedelta(hours=SLA_VENCIDO_HORAS)

    # KPIs sobre el universo visible del usuario (sin los filtros de arriba,
    # para que la cabecera no cambie cuando se filtra la tabla).
    activos_qs   = base_qs.exclude(status__in=CERRADOS)
    kpi_activos  = activos_qs.count()
    kpi_criticos_sin_asignar = activos_qs.filter(priority='critica', assignedTo__isnull=True).count()
    kpi_vencidos = activos_qs.filter(createdAt__lt=corte_vencido).count()

    resueltos = base_qs.filter(closedAt__isnull=False)
    if resueltos.exists():
        total_horas = sum((t.closedAt - t.createdAt).total_seconds() / 3600 for t in resueltos)
        kpi_resolucion_dias = round(total_horas / resueltos.count() / 24, 1)
    else:
        kpi_resolucion_dias = None

    if vista == 'vencidos':
        tickets = tickets.filter(createdAt__lt=corte_vencido).exclude(status__in=CERRADOS)
    elif vista == 'criticos':
        tickets = tickets.filter(priority='critica').exclude(status__in=CERRADOS)
    elif vista == 'activos':
        tickets = tickets.exclude(status__in=CERRADOS)

    tickets = list(tickets)
    for t in tickets:
        t.vencido = (ahora - t.createdAt) > timedelta(hours=SLA_VENCIDO_HORAS) and t.status not in CERRADOS

    if is_superadmin(request.user):
        areas_disponibles = Area.objects.all()
    elif is_area_admin(request.user) or is_agent(request.user):
        areas_disponibles = Area.objects.filter(areaName__in=get_allowed_area_names(request.user))
    else:
        areas_disponibles = Area.objects.none()

    return render(request, 'tickets/list.html', {
        'tickets':           tickets,
        'areas_disponibles': areas_disponibles,
        'status_filter':     status_filter,
        'priority_filter':   priority_filter,
        'area_filter':       area_filter,
        'q':                 q,
        'vista':             vista,
        'puede_gestionar':   is_superadmin(request.user) or is_area_admin(request.user) or is_agent(request.user),
        'kpi_activos':            kpi_activos,
        'kpi_criticos_sin_asignar': kpi_criticos_sin_asignar,
        'kpi_vencidos':           kpi_vencidos,
        'kpi_resolucion_dias':    kpi_resolucion_dias,
    })


@login_required
def ticketCreateView(request):
    areas = Area.objects.all()

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        priority    = request.POST.get('priority', 'media')
        area_id     = request.POST.get('area')
        category_id = request.POST.get('category')

        if not title or not description or not area_id or not category_id:
            messages.error(request, 'Todos los campos son obligatorios.')
        else:
            try:
                area     = Area.objects.get(areaId=area_id)
                category = TicketCategory.objects.get(categoryId=category_id, area=area)

                last          = Ticket.objects.order_by('-ticketId').first()
                next_num      = (last.ticketId + 1) if last else 1
                ticket_number = f'TKT-{next_num:05d}'

                ticket = Ticket.objects.create(
                    ticketNumber=ticket_number,
                    title=title,
                    description=description,
                    priority=priority,
                    createdBy=request.user,
                    area=area,
                    category=category,
                )

                _notificar_ticket(
                    ticket, 'ticket_nuevo',
                    f'Nuevo ticket en {area.areaName}',
                    f'{request.user.name} {request.user.lastname} creó el ticket "{title}" '
                    f'con prioridad {priority}.',
                    actor=request.user,
                )

                messages.success(request, f'Ticket {ticket.ticketNumber} creado correctamente.')
                return redirect('tickets:detail', pk=ticket.ticketId)

            except (Area.DoesNotExist, TicketCategory.DoesNotExist):
                messages.error(request, 'Área o categoría no válida.')
            except Exception as e:
                messages.error(request, f'Error al crear el ticket: {e}')

    return render(request, 'tickets/create.html', {'areas': areas})


@login_required
def ticketDetailView(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if not _can_access_ticket(request.user, ticket):
        messages.error(request, 'No tienes permiso para ver este ticket.')
        return redirect('tickets:list')

    comments = ticket.comments.select_related('user').order_by('createdAt')
    history  = ticket.statusHistory.select_related('changedBy').order_by('-changedAt')
    agentes, puede_asignar = _agentes_asignables_para(ticket, request.user)

    antiguedad_horas = (timezone.now() - ticket.createdAt).total_seconds() / 3600
    vencido = antiguedad_horas > SLA_VENCIDO_HORAS and ticket.status not in CERRADOS

    return render(request, 'tickets/detail.html', {
        'ticket':          ticket,
        'comments':        comments,
        'history':         history,
        'puede_gestionar': _can_manage_ticket(request.user, ticket),
        'agentes':         agentes,
        'puede_asignar':   puede_asignar,
        'vencido':         vencido,
    })


@login_required
def ticketUpdateView(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user   = request.user

    if not _can_manage_ticket(user, ticket):
        messages.error(request, 'No tienes permiso para modificar este ticket.')
        return redirect('tickets:detail', pk=pk)

    agentes, puede_asignar = _agentes_asignables_para(ticket, user)

    if request.method == 'POST':
        old_status = ticket.status
        new_status = request.POST.get('status', ticket.status)
        priority   = request.POST.get('priority', ticket.priority)
        comment    = request.POST.get('comment', '').strip()

        ticket.priority = priority

        if new_status != old_status:
            ticket.status = new_status
            if new_status in ('cerrado', 'resuelto'):
                ticket.closedAt = datetime.now()
            elif new_status != 'cerrado' and new_status != 'resuelto':
                # Si se reabre, limpiar closedAt
                if old_status in ('cerrado', 'resuelto'):
                    ticket.closedAt = None
            TicketStatusHistory.objects.create(
                ticket=ticket, oldStatus=old_status,
                newStatus=new_status, changedBy=user,
            )
            _notificar_ticket(
                ticket, 'ticket_estado',
                f'Ticket {ticket.ticketNumber} — estado actualizado',
                f'{user.name} {user.lastname} cambió el estado de "{old_status}" a "{new_status}".',
                actor=user,
            )

        if puede_asignar:
            assigned_id = request.POST.get('assigned_to', '').strip()
            if assigned_id:
                from apps.users.models import User as UserModel
                try:
                    asignado = UserModel.objects.get(pk=assigned_id)
                    if agentes.filter(pk=asignado.pk).exists():
                        old_assigned = ticket.assignedTo
                        ticket.assignedTo = asignado
                        if old_assigned != asignado:
                            _notificar_ticket(
                                ticket, 'ticket_asignado',
                                f'Ticket {ticket.ticketNumber} asignado',
                                f'{user.name} {user.lastname} asignó el ticket "{ticket.title}" '
                                f'a {asignado.name} {asignado.lastname}.',
                                actor=user,
                            )
                    else:
                        messages.error(request, 'No puedes asignar ese agente a este ticket.')
                        return redirect('tickets:update', pk=pk)
                except UserModel.DoesNotExist:
                    ticket.assignedTo = None
            else:
                ticket.assignedTo = None

        ticket.save()

        if comment:
            TicketComment.objects.create(ticket=ticket, user=user, comment=comment)
            _notificar_ticket(
                ticket, 'ticket_comentario',
                f'Nuevo comentario en {ticket.ticketNumber}',
                f'{user.name} {user.lastname} comentó: "{comment[:100]}{"..." if len(comment) > 100 else ""}"',
                actor=user,
            )

        messages.success(request, 'Ticket actualizado correctamente.')
        return redirect('tickets:detail', pk=pk)

    return render(request, 'tickets/update.html', {
        'ticket':        ticket,
        'puede_asignar': puede_asignar,
        'agentes':       agentes,
        'user':          user,
    })


@login_required
def ticketAddCommentView(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if not _can_access_ticket(request.user, ticket):
        messages.error(request, 'No tienes permiso para comentar en este ticket.')
        return redirect('tickets:list')

    if request.method == 'POST':
        comment_text = request.POST.get('comment', '').strip()
        if comment_text:
            TicketComment.objects.create(ticket=ticket, user=request.user, comment=comment_text)
            _notificar_ticket(
                ticket, 'ticket_comentario',
                f'Nuevo comentario en {ticket.ticketNumber}',
                f'{request.user.name} {request.user.lastname} comentó: '
                f'"{comment_text[:100]}{"..." if len(comment_text) > 100 else ""}"',
                actor=request.user,
            )
            messages.success(request, 'Comentario agregado.')
        else:
            messages.error(request, 'El comentario no puede estar vacío.')

    return redirect('tickets:detail', pk=pk)


@login_required
def categoriasPorAreaView(request, area_id):
    from django.http import JsonResponse
    try:
        area = Area.objects.get(areaId=area_id)
    except Area.DoesNotExist:
        return JsonResponse([], safe=False)

    categorias = list(
        TicketCategory.objects
        .filter(area=area)
        .order_by('categoryName')
        .values('categoryId', 'categoryName')
    )

    if not any(c['categoryName'].strip().lower() == 'otras' for c in categorias):
        try:
            nueva_categoria = TicketCategory.objects.create(area=area, categoryName='Otras')
            categorias.append({
                'categoryId': nueva_categoria.categoryId,
                'categoryName': nueva_categoria.categoryName,
            })
        except Exception:
            pass

    categorias.sort(key=lambda c: (c['categoryName'].strip().lower() == 'otras', c['categoryName']))
    return JsonResponse(categorias, safe=False)


@login_required
def notificacionesView(request):
    """Lista de notificaciones del usuario actual."""
    from apps.core.models import Notification

    # Marcar como leídas las que se estén viendo
    if request.method == 'POST' and request.POST.get('action') == 'marcar_leidas':
        Notification.objects.filter(destinatario=request.user, leida=False).update(leida=True)
        messages.success(request, 'Todas las notificaciones marcadas como leídas.')
        return redirect('tickets:notificaciones')

    notificaciones = Notification.objects.filter(
        destinatario=request.user
    ).order_by('-createdAt')[:50]

    no_leidas = Notification.objects.filter(
        destinatario=request.user, leida=False
    ).count()

    return render(request, 'tickets/notificaciones.html', {
        'notificaciones': notificaciones,
        'no_leidas':      no_leidas,
    })


@login_required
def notificacionesCountView(request):
    """Endpoint JSON para el contador de notificaciones en el navbar y para
    el toast de "te asignaron un ticket" -- devuelve también la más
    reciente sin leer, para que el JS decida si ya la mostró o no."""
    from django.http import JsonResponse
    from apps.core.models import Notification

    no_leidas = Notification.objects.filter(destinatario=request.user, leida=False)
    count = no_leidas.count()
    ultima = no_leidas.order_by('-createdAt').first()

    return JsonResponse({
        'count': count,
        'latest': {
            'id':        ultima.notifId,
            'titulo':    ultima.titulo,
            'mensaje':   ultima.mensaje,
            'ticket_id': ultima.ticket_id,
        } if ultima else None,
    })


@login_required
def reportesView(request):
    """Métricas reales sobre los mismos tickets que ya ve este usuario en
    la lista -- nada aquí viene de una tabla nueva, son agregados sobre
    Ticket/TicketStatusHistory."""
    from apps.users.models import User

    tickets = _tickets_for_user(request.user)
    total = tickets.count()
    ahora = timezone.now()

    por_area = list(
        tickets.values('area__areaName')
        .annotate(n=Count('ticketId'))
        .order_by('-n')
    )

    estado_dict = {
        row['status']: row['n']
        for row in tickets.values('status').annotate(n=Count('ticketId'))
    }
    ESTADOS_COLOR = {
        'abierto':    'var(--accent)',
        'en_proceso': 'var(--accent-h)',
        'pendiente':  'var(--warning)',
        'en_espera':  'var(--muted2)',
        'escalado':   'var(--danger)',
        'resuelto':   'var(--success)',
        'cerrado':    'var(--muted2)',
    }
    estados_data = [
        {'estado': val, 'label': label, 'color': ESTADOS_COLOR[val], 'n': estado_dict.get(val, 0)}
        for val, label in TicketStatusChoices.choices
        if estado_dict.get(val, 0) > 0
    ]

    resueltos = tickets.filter(closedAt__isnull=False)
    if resueltos.exists():
        total_horas = sum((t.closedAt - t.createdAt).total_seconds() / 3600 for t in resueltos)
        resolucion_prom_dias = round(total_horas / resueltos.count() / 24, 1)
    else:
        resolucion_prom_dias = None

    sin_asignar_24h = (
        tickets.filter(assignedTo__isnull=True, createdAt__lt=ahora - timedelta(hours=24))
        .exclude(status__in=CERRADOS).count()
    )
    pct_sin_asignar = round(100 * sin_asignar_24h / total) if total else 0

    reabiertos = (
        TicketStatusHistory.objects.filter(ticket__in=tickets, oldStatus__in=CERRADOS)
        .values('ticket').distinct().count()
    )

    carga_agentes = []
    agentes_con_tickets = User.objects.filter(ticketsAssigned__in=tickets).distinct().select_related('area')
    for ag in agentes_con_tickets:
        asignados = tickets.filter(assignedTo=ag)
        resueltos_ag = asignados.filter(closedAt__isnull=False)
        if resueltos_ag.exists():
            h = sum((t.closedAt - t.createdAt).total_seconds() / 3600 for t in resueltos_ag)
            prom = round(h / resueltos_ag.count() / 24, 1)
        else:
            prom = None
        carga_agentes.append({
            'nombre':    f'{ag.name} {ag.lastname}'.strip(),
            'area':      ag.area.areaName if ag.area else '—',
            'asignados': asignados.count(),
            'prom':      prom,
        })
    carga_agentes.sort(key=lambda x: -x['asignados'])

    # Mapa de calor asignado × prioridad -- solo para quien puede gestionar
    # tickets (ver quién concentra qué tanta carga de cada severidad es una
    # decisión de admin de área/superadmin, no de un usuario final).
    heatmap = None
    puede_ver_heatmap = is_superadmin(request.user) or is_area_admin(request.user)
    if puede_ver_heatmap:
        prioridades = list(TicketPriorityChoices.choices)  # [(baja,'Baja'), ...]
        conteo = {}
        for row in tickets.values('assignedTo_id', 'assignedTo__name', 'assignedTo__lastname', 'priority').annotate(n=Count('ticketId')):
            clave = row['assignedTo_id']
            conteo.setdefault(clave, {'nombre': (
                f"{row['assignedTo__name']} {row['assignedTo__lastname']}".strip()
                if row['assignedTo_id'] else 'Sin asignar'
            ), 'celdas': {}})
            conteo[clave]['celdas'][row['priority']] = row['n']

        heatmap_max = 0
        heatmap_rows = []
        for clave, datos in conteo.items():
            fila = {'nombre': datos['nombre'], 'asignado_id': clave or '', 'celdas': [], 'total': 0}
            for val, _ in prioridades:
                n = datos['celdas'].get(val, 0)
                fila['celdas'].append({'prioridad': val, 'n': n})
                fila['total'] += n
                heatmap_max = max(heatmap_max, n)
            heatmap_rows.append(fila)
        # "Sin asignar" siempre al final, el resto por carga total descendente
        heatmap_rows.sort(key=lambda f: (f['nombre'] == 'Sin asignar', -f['total']))

        for fila in heatmap_rows:
            for celda in fila['celdas']:
                ratio = (celda['n'] / heatmap_max) if heatmap_max else 0
                celda['color'] = _color_mapa_calor(ratio) if celda['n'] else 'var(--surface2)'
                celda['texto_claro'] = ratio > 0.62

        heatmap = {
            'columnas': [label for _, label in prioridades],
            'filas':    heatmap_rows,
            'max':      heatmap_max,
        }

    return render(request, 'tickets/reportes.html', {
        'total':                 total,
        'por_area':              por_area,
        'estados_data':          estados_data,
        'resolucion_prom_dias':  resolucion_prom_dias,
        'pct_sin_asignar':       pct_sin_asignar,
        'reabiertos':            reabiertos,
        'carga_agentes':         carga_agentes,
        'heatmap':               heatmap,
    })


@login_required
def heatmapDetalleView(request):
    """JSON para el popup del mapa de calor: los tickets exactos detrás de
    una celda (asignado × prioridad). Mismo alcance que reportesView -- no
    es una puerta nueva a datos que este usuario no pudiera ver ya."""
    from django.http import JsonResponse
    from django.urls import reverse

    if not (is_superadmin(request.user) or is_area_admin(request.user)):
        return JsonResponse({'error': 'No autorizado'}, status=403)

    priority = request.GET.get('priority', '')
    assigned_to = request.GET.get('assigned_to', '')

    tickets = _tickets_for_user(request.user)
    if priority:
        tickets = tickets.filter(priority=priority)
    if assigned_to:
        tickets = tickets.filter(assignedTo_id=assigned_to)
    else:
        tickets = tickets.filter(assignedTo__isnull=True)

    data = [{
        'ticketNumber': t.ticketNumber,
        'title':        t.title,
        'area':         t.area.areaName,
        'status':       t.get_status_display(),
        'createdAt':    t.createdAt.strftime('%d/%m/%Y'),
        'url':          reverse('tickets:detail', args=[t.ticketId]),
    } for t in tickets.select_related('area').order_by('-createdAt')]

    return JsonResponse({'tickets': data})
