"""
apps/core/permissions.py
========================
Utilidades de permisos basadas en el nombre del rol.

Jerarquía:
  Super Admin  → acceso total (is_superuser=True o rol "Administrador")
  Area Admin   → gestiona usuarios y ve tickets solo de sus áreas asignadas
  Agente       → solo interactúa con tickets de su área
  Usuario      → solo crea y sigue sus propios tickets

NOTA: Los nombres de rol deben coincidir EXACTAMENTE con los registros de la BD.
Si cambias un nombre en la BD, actualiza los diccionarios aquí.
"""

from functools import wraps
from django.conf import settings
from django.shortcuts import redirect
from django.contrib import messages


# ─── Configuración central de roles ──────────────────────────────────────────

SUPERADMIN_ROLE_NAMES = {
    'Administrador',
}

# Admin de área → áreas que gestiona
AREA_ADMIN_ROLE_MAP = {
    'Administración de Talento Humano':     ['Talento Humano'],
    'Administrador Administración/Finance': ['Administracion', 'Finance'],
    'Administrador Sistemas':               ['Sistemas'],
}

# Agente → área(s) a las que responde tickets
AGENT_ROLE_MAP = {
    'Agente Administración':    ['Administracion'],
    'Agente Finance':           ['Finance'],
    'Agente Sistemas':          ['Sistemas'],
    'Agente Talento Humano':    ['Talento Humano'],
    'Agente Archivo':           ['Archivo'],
}

USER_ROLE_NAMES = {
    'Usuario',
}

# Contraseña maestra requerida para crear o eliminar un super admin.
# Vive en settings (y en el .env del servidor), nunca en texto plano aquí.
SUPERADMIN_MASTER_PASSWORD = settings.SUPERADMIN_MASTER_PASSWORD


# ─── Helpers básicos ──────────────────────────────────────────────────────────

def _role_name(user):
    try:
        return user.role.roleName
    except Exception:
        return ''


def _user_area_name(user):
    """Área singular almacenada en el campo FK del usuario."""
    try:
        return user.area.areaName
    except Exception:
        return ''


def is_superadmin(user):
    return user.is_superuser or _role_name(user) in SUPERADMIN_ROLE_NAMES


def is_area_admin(user):
    return not is_superadmin(user) and _role_name(user) in AREA_ADMIN_ROLE_MAP


def is_agent(user):
    return _role_name(user) in AGENT_ROLE_MAP


def is_end_user(user):
    return _role_name(user) in USER_ROLE_NAMES


def get_allowed_area_names(user):
    """
    Áreas que el usuario puede gestionar/ver.

    Estrategia en tres capas:
    1. Consulta la tabla user_area_assignments (asignaciones múltiples explícitas)
    2. Busca el rol en AREA_ADMIN_ROLE_MAP / AGENT_ROLE_MAP por nombre exacto
    3. Añade el área FK del usuario como respaldo mínimo.

    Super admin → [] (señal de acceso total, se maneja en cada vista).
    """
    if is_superadmin(user):
        return []

    areas = []

    # 1. Áreas asignadas explícitamente en user_area_assignments
    try:
        from apps.users.models import UserAreaAssignment
        assigned = list(
            UserAreaAssignment.objects.filter(user=user)
            .values_list('area__areaName', flat=True)
        )
        for a in assigned:
            if a and a not in areas:
                areas.append(a)
    except Exception:
        pass

    # 2. Mapeo estático por nombre de rol
    role = _role_name(user)
    if role in AREA_ADMIN_ROLE_MAP:
        for a in AREA_ADMIN_ROLE_MAP[role]:
            if a not in areas:
                areas.append(a)
    elif role in AGENT_ROLE_MAP:
        for a in AGENT_ROLE_MAP[role]:
            if a not in areas:
                areas.append(a)

    # 3. Respaldo: siempre incluir el área FK del usuario
    user_area = _user_area_name(user)
    if user_area and user_area not in areas:
        areas.append(user_area)

    return areas


def get_creatable_agent_role_names(user):
    """
    Nombres de rol que un admin de área puede asignar al crear/editar usuarios.

    Reglas:
    - Solo roles de tipo AGENTE (no superadmin, no otro admin de área, no Usuario)
    - Solo agentes cuya área esté dentro de las áreas que gestiona el admin

    Ejemplo: Administrador Administración/Finance gestiona ['Administracion','Finance'],
    por lo que puede crear 'Agente Administración' y 'Agente Finance',
    pero NO 'Agente Sistemas'.
    """
    if is_superadmin(user):
        return list(AGENT_ROLE_MAP.keys())  # super admin puede asignar cualquier agente

    allowed_areas = set(get_allowed_area_names(user))
    creatable = []
    for role_name, areas in AGENT_ROLE_MAP.items():
        # El rol de agente es creatable si AL MENOS UNA de sus áreas está en las del admin
        if allowed_areas.intersection(areas):
            creatable.append(role_name)
    return creatable


def can_manage_panel(user):
    return is_superadmin(user) or is_area_admin(user)


def can_manage_global_config(user):
    return is_superadmin(user)


def can_assign_tickets(user):
    """Solo los admins de área (y super admin) pueden asignar tickets a agentes."""
    return is_superadmin(user) or is_area_admin(user)


def get_assignable_agents(ticket_area_name, assigning_user):
    """
    Devuelve el queryset de agentes que pueden ser asignados a un ticket.

    - El asignador debe ser admin de área o super admin.
    - Solo aparecen agentes cuyo rol de agente cubre el área del ticket.
    - El admin de área solo puede asignar agentes de SUS propias áreas.
    """
    from apps.users.models import User

    # Roles de agente que cubren el área del ticket
    valid_agent_roles = [
        role_name
        for role_name, areas in AGENT_ROLE_MAP.items()
        if ticket_area_name in areas
    ]

    if not valid_agent_roles:
        return User.objects.none()

    qs = User.objects.filter(
        role__roleName__in=valid_agent_roles,
        status='activo',
    ).select_related('role', 'area')

    # Admin de área: además, solo agentes de sus propias áreas
    if is_area_admin(assigning_user):
        allowed = get_allowed_area_names(assigning_user)
        if ticket_area_name not in allowed:
            return User.objects.none()  # no debería llegar aquí, pero por seguridad
        qs = qs.filter(area__areaName__in=allowed)

    return qs


# ─── Decoradores ─────────────────────────────────────────────────────────────

def superadmin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not is_superadmin(request.user):
            messages.error(request, 'Solo los super administradores pueden acceder a esta sección.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def panel_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('users:login')
        if not can_manage_panel(request.user):
            messages.error(request, 'No tienes permiso para acceder al panel de administración.')
            return redirect('core:dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper
