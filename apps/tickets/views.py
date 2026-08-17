"""
apps/tickets/views.py — con notificaciones, filtros y validación cédula
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime

from .models import Ticket, TicketCategory, TicketComment, TicketStatusHistory
from apps.core.models import Area
from apps.core.permissions import (
    is_superadmin, is_area_admin, is_agent,
    get_allowed_area_names, can_assign_tickets, get_assignable_agents,
)


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


def _notificar_ticket(ticket, tipo, titulo, mensaje, actor):
    """Crea notificaciones internas para el área del ticket."""
    try:
        from apps.core.models import Notification
        Notification.crear_para_area(
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
        # Notificar al agente asignado si existe y no es el actor
        if ticket.assignedTo and ticket.assignedTo != actor:
            Notification.crear(
                destinatario=ticket.assignedTo,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                ticket=ticket,
            )
    except Exception:
        pass  # Notificaciones no bloquean el flujo principal


# ─── Vistas ───────────────────────────────────────────────────────────────────

@login_required
def ticketListView(request):
    tickets = _tickets_for_user(request.user).order_by('-createdAt')

    status_filter   = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    area_filter     = request.GET.get('area', '')

    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    if area_filter:
        tickets = tickets.filter(area__areaId=area_filter)

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
        'puede_gestionar':   is_superadmin(request.user) or is_area_admin(request.user) or is_agent(request.user),
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

    return render(request, 'tickets/detail.html', {
        'ticket':          ticket,
        'comments':        comments,
        'history':         history,
        'puede_gestionar': _can_manage_ticket(request.user, ticket),
    })


@login_required
def ticketUpdateView(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user   = request.user

    if not _can_manage_ticket(user, ticket):
        messages.error(request, 'No tienes permiso para modificar este ticket.')
        return redirect('tickets:detail', pk=pk)

    puede_asignar = can_assign_tickets(user)

    # Admins de área pueden asignarse a sí mismos además de a los agentes
    if puede_asignar:
        agentes = get_assignable_agents(ticket.area.areaName, user)
        # Si el admin de área está en el área del ticket, incluirse a sí mismo
        if is_area_admin(user) or is_superadmin(user):
            from apps.users.models import User as UserModel
            from django.db.models import Q
            # Incluir al admin actual como opción de asignación
            admin_qs = UserModel.objects.filter(pk=user.pk)
            from django.db.models import QuerySet
            # Combinar agentes + el propio admin
            agentes = (agentes | admin_qs).distinct()
    else:
        agentes = None

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
    """Endpoint JSON para el contador de notificaciones en el navbar."""
    from django.http import JsonResponse
    from apps.core.models import Notification

    count = Notification.objects.filter(
        destinatario=request.user, leida=False
    ).count()
    return JsonResponse({'count': count})
