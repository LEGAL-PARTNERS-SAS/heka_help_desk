"""
apps/core/views.py
==================
Dashboard principal adaptado al rol del usuario.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from apps.tickets.models import Ticket
from apps.core.permissions import (
    is_superadmin, is_area_admin, is_agent,
    get_allowed_area_names,
)


@login_required
def dashboardView(request):
    user = request.user

    # Obtener el queryset correcto según el rol
    if is_superadmin(user):
        tickets_qs = Ticket.objects.all()
    elif is_area_admin(user) or is_agent(user):
        allowed = get_allowed_area_names(user)
        tickets_qs = Ticket.objects.filter(area__areaName__in=allowed)
    else:
        # Usuario final: solo sus propios tickets
        tickets_qs = Ticket.objects.filter(createdBy=user)

    stats = {
        'abiertos':   tickets_qs.filter(status='abierto').count(),
        'en_proceso': tickets_qs.filter(status='en_proceso').count(),
        'cerrados':   tickets_qs.filter(status='cerrado').count(),
        'total':      tickets_qs.count(),
    }

    tickets_recientes = tickets_qs.select_related('area', 'category').order_by('-createdAt')[:5]

    return render(request, 'core/dashboard.html', {
        'stats':             stats,
        'tickets_recientes': tickets_recientes,
        'es_superadmin':     is_superadmin(user),
        'es_area_admin':     is_area_admin(user),
        'es_agente':         is_agent(user),
    })
