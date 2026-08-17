"""
apps/admin_panel/views.py
=========================
Panel de administración con control de acceso por área y rol.

Acceso:
  Super Admin     → todo el panel (áreas, roles, categorías, TODOS los usuarios)
  Admin de Área   → solo puede gestionar usuarios de SUS áreas
                    NO puede crear/editar áreas, roles ni categorías globales
  Agente / Usuario → sin acceso al panel
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.core.models import Area, Role
from apps.users.models import User
from apps.tickets.models import TicketCategory, Ticket

from apps.core.permissions import (
    panel_required, superadmin_required,
    is_superadmin, is_area_admin,
    get_allowed_area_names, can_manage_global_config,
    get_creatable_agent_role_names, SUPERADMIN_MASTER_PASSWORD,
)


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@panel_required
def adminDashboardView(request):
    user = request.user

    if is_superadmin(user):
        context = {
            'total_areas':    Area.objects.count(),
            'total_roles':    Role.objects.count(),
            'total_usuarios': User.objects.count(),
            'total_cats':     TicketCategory.objects.count(),
        }
    else:
        # Admin de área: solo muestra datos de sus áreas
        allowed = get_allowed_area_names(user)
        context = {
            'total_areas':    Area.objects.filter(areaName__in=allowed).count(),
            'total_roles':    None,   # no tiene acceso a roles globales
            'total_usuarios': User.objects.filter(area__areaName__in=allowed).count(),
            'total_cats':     TicketCategory.objects.filter(area__areaName__in=allowed).count(),
        }

    context['es_superadmin'] = is_superadmin(user)
    return render(request, 'admin_panel/dashboard.html', context)


# ══════════════════════════════════════════════════════════════════════════════
# ÁREAS  (solo super admin)
# ══════════════════════════════════════════════════════════════════════════════

@superadmin_required
def areaListView(request):
    areas = Area.objects.all().order_by('areaName')
    return render(request, 'admin_panel/areas/list.html', {'areas': areas})


@superadmin_required
def areaCreateView(request):
    if request.method == 'POST':
        name = request.POST.get('area_name', '').strip()
        if not name:
            messages.error(request, 'El nombre del área es obligatorio.')
        elif Area.objects.filter(areaName=name).exists():
            messages.error(request, f'El área "{name}" ya existe.')
        else:
            Area.objects.create(areaName=name)
            messages.success(request, f'Área "{name}" creada correctamente.')
            return redirect('admin_panel:areas')
    return render(request, 'admin_panel/areas/form.html', {'accion': 'Crear'})


@superadmin_required
def areaEditView(request, pk):
    area = get_object_or_404(Area, areaId=pk)
    if request.method == 'POST':
        name = request.POST.get('area_name', '').strip()
        if not name:
            messages.error(request, 'El nombre es obligatorio.')
        elif Area.objects.filter(areaName=name).exclude(areaId=pk).exists():
            messages.error(request, f'El área "{name}" ya existe.')
        else:
            area.areaName = name
            area.save()
            messages.success(request, 'Área actualizada.')
            return redirect('admin_panel:areas')
    return render(request, 'admin_panel/areas/form.html', {'accion': 'Editar', 'area': area})


@superadmin_required
def areaDeleteView(request, pk):
    area = get_object_or_404(Area, areaId=pk)
    if request.method == 'POST':
        try:
            area.delete()
            messages.success(request, 'Área eliminada.')
        except Exception:
            messages.error(request, 'No se puede eliminar: tiene usuarios o categorías asociadas.')
        return redirect('admin_panel:areas')
    return render(request, 'admin_panel/confirm_delete.html', {
        'objeto': area.areaName, 'tipo': 'Área',
        'cancel_url': 'admin_panel:areas'
    })


# ══════════════════════════════════════════════════════════════════════════════
# ROLES  (solo super admin)
# ══════════════════════════════════════════════════════════════════════════════

@superadmin_required
def roleListView(request):
    roles = Role.objects.all().order_by('roleName')
    return render(request, 'admin_panel/roles/list.html', {'roles': roles})


@superadmin_required
def roleCreateView(request):
    if request.method == 'POST':
        name = request.POST.get('role_name', '').strip()
        desc = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'El nombre del rol es obligatorio.')
        elif Role.objects.filter(roleName=name).exists():
            messages.error(request, f'El rol "{name}" ya existe.')
        else:
            Role.objects.create(roleName=name, description=desc)
            messages.success(request, f'Rol "{name}" creado.')
            return redirect('admin_panel:roles')
    return render(request, 'admin_panel/roles/form.html', {'accion': 'Crear'})


@superadmin_required
def roleEditView(request, pk):
    role = get_object_or_404(Role, roleId=pk)
    if request.method == 'POST':
        name = request.POST.get('role_name', '').strip()
        desc = request.POST.get('description', '').strip()
        if not name:
            messages.error(request, 'El nombre es obligatorio.')
        else:
            role.roleName    = name
            role.description = desc
            role.save()
            messages.success(request, 'Rol actualizado.')
            return redirect('admin_panel:roles')
    return render(request, 'admin_panel/roles/form.html', {'accion': 'Editar', 'role': role})


@superadmin_required
def roleDeleteView(request, pk):
    role = get_object_or_404(Role, roleId=pk)
    if request.method == 'POST':
        try:
            role.delete()
            messages.success(request, 'Rol eliminado.')
        except Exception:
            messages.error(request, 'No se puede eliminar: tiene usuarios asociados.')
        return redirect('admin_panel:roles')
    return render(request, 'admin_panel/confirm_delete.html', {
        'objeto': role.roleName, 'tipo': 'Rol',
        'cancel_url': 'admin_panel:roles'
    })


# ══════════════════════════════════════════════════════════════════════════════
# CATEGORÍAS  (solo super admin)
# ══════════════════════════════════════════════════════════════════════════════

@superadmin_required
def categoryListView(request):
    categories = TicketCategory.objects.all().select_related('area').order_by('area__areaName', 'categoryName')
    return render(request, 'admin_panel/categories/list.html', {'categories': categories})


@superadmin_required
def categoryCreateView(request):
    areas = Area.objects.all()
    if request.method == 'POST':
        name    = request.POST.get('category_name', '').strip()
        area_id = request.POST.get('area')
        if not name or not area_id:
            messages.error(request, 'Nombre y área son obligatorios.')
        else:
            try:
                area = Area.objects.get(areaId=area_id)
                TicketCategory.objects.create(categoryName=name, area=area)
                messages.success(request, f'Categoría "{name}" creada.')
                return redirect('admin_panel:categories')
            except Area.DoesNotExist:
                messages.error(request, 'Área no válida.')
    return render(request, 'admin_panel/categories/form.html', {'accion': 'Crear', 'areas': areas})


@superadmin_required
def categoryEditView(request, pk):
    category = get_object_or_404(TicketCategory, categoryId=pk)
    areas    = Area.objects.all()
    if request.method == 'POST':
        name    = request.POST.get('category_name', '').strip()
        area_id = request.POST.get('area')
        if not name or not area_id:
            messages.error(request, 'Nombre y área son obligatorios.')
        else:
            try:
                category.categoryName = name
                category.area         = Area.objects.get(areaId=area_id)
                category.save()
                messages.success(request, 'Categoría actualizada.')
                return redirect('admin_panel:categories')
            except Area.DoesNotExist:
                messages.error(request, 'Área no válida.')
    return render(request, 'admin_panel/categories/form.html', {
        'accion': 'Editar', 'areas': areas, 'category': category
    })


@superadmin_required
def categoryDeleteView(request, pk):
    category = get_object_or_404(TicketCategory, categoryId=pk)
    if request.method == 'POST':
        try:
            category.delete()
            messages.success(request, 'Categoría eliminada.')
        except Exception:
            messages.error(request, 'No se puede eliminar: tiene tickets asociados.')
        return redirect('admin_panel:categories')
    return render(request, 'admin_panel/confirm_delete.html', {
        'objeto': category.categoryName, 'tipo': 'Categoría',
        'cancel_url': 'admin_panel:categories'
    })


# ══════════════════════════════════════════════════════════════════════════════
# USUARIOS  (super admin ve todos; admin de área ve solo los de su área)
# ══════════════════════════════════════════════════════════════════════════════

@panel_required
def userAdminListView(request):
    if is_superadmin(request.user):
        usuarios = User.objects.all().select_related('role', 'area').order_by('lastname', 'name')
    else:
        allowed  = get_allowed_area_names(request.user)
        usuarios = (
            User.objects
            .filter(area__areaName__in=allowed)
            .exclude(is_superuser=True)          # admins de área nunca ven superadmins
            .exclude(role__roleName__in=SUPERADMIN_ROLE_NAMES)
            .select_related('role', 'area')
            .order_by('lastname', 'name')
        )
    return render(request, 'admin_panel/users/list.html', {
        'usuarios':      usuarios,
        'es_superadmin': is_superadmin(request.user),
    })


@panel_required
def userAdminCreateView(request):
    user = request.user

    # Super admin ve todas las áreas; admin de área solo las suyas
    if is_superadmin(user):
        areas = Area.objects.all()
        roles = Role.objects.all()
    else:
        # Admin de área: solo puede crear agentes de SUS propias áreas.
        allowed = get_allowed_area_names(user)
        areas   = Area.objects.filter(areaName__in=allowed)
        creatable_role_names = get_creatable_agent_role_names(user)
        roles = Role.objects.filter(roleName__in=creatable_role_names)

    if request.method == 'POST':
        data = {
            'name':     request.POST.get('name', '').strip(),
            'lastname': request.POST.get('lastname', '').strip(),
            'email':    request.POST.get('email', '').strip(),
            'role':     request.POST.get('role'),
        }
        # Múltiples áreas: getlist devuelve lista de IDs seleccionados
        area_ids = request.POST.getlist('areas')
        password        = request.POST.get('password', '')
        will_superadmin = request.POST.get('is_superuser') == 'on'

        if not area_ids:
            messages.error(request, 'Debes seleccionar al menos un área.')
            return render(request, 'admin_panel/users/form.html', {
                'accion': 'Crear', 'areas': areas, 'roles': roles, 'es_superadmin': is_superadmin(user),
            })

        # ── Bloque 1: solo super admin puede crear super admins ──────────────
        if will_superadmin and not is_superadmin(user):
            messages.error(request, 'Solo un super administrador puede crear otros super administradores.')
            return render(request, 'admin_panel/users/form.html', {
                'accion': 'Crear', 'areas': areas, 'roles': roles, 'es_superadmin': is_superadmin(user),
            })

        # ── Bloque 2: contraseña maestra al crear super admin ────────────────
        if will_superadmin and is_superadmin(user):
            master_pw = request.POST.get('master_password', '')
            if master_pw != SUPERADMIN_MASTER_PASSWORD:
                messages.error(request, 'Contraseña maestra incorrecta. No se puede crear el super administrador.')
                return render(request, 'admin_panel/users/form.html', {
                    'accion': 'Crear', 'areas': areas, 'roles': roles,
                    'es_superadmin': is_superadmin(user), 'requiere_master': True,
                })

        # ── Bloque 3: admin de área no puede tocar áreas fuera de su scope ──
        if not is_superadmin(user):
            allowed = get_allowed_area_names(user)
            selected_areas = Area.objects.filter(areaId__in=area_ids)
            for sa in selected_areas:
                if sa.areaName not in allowed:
                    messages.error(request, f'No tienes permiso para crear usuarios en el área "{sa.areaName}".')
                    return render(request, 'admin_panel/users/form.html', {
                        'accion': 'Crear', 'areas': areas, 'roles': roles, 'es_superadmin': False,
                    })

        if User.objects.filter(email=data['email']).exists():
            messages.error(request, 'Ya existe una cuenta con ese email.')
        elif len(password) < 6:
            messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
        else:
            try:
                # Área principal = primera seleccionada
                primary_area = Area.objects.get(areaId=area_ids[0])
                new_user = User(
                    name=data['name'],
                    lastname=data['lastname'],
                    email=data['email'],
                    role=Role.objects.get(roleId=data['role']),
                    area=primary_area,
                    is_staff=request.POST.get('is_staff') == 'on' and is_superadmin(user),
                    is_superuser=request.POST.get('is_superuser') == 'on' and is_superadmin(user),
                    status='activo',
                )
                new_user.set_password(password)
                new_user.save()

                # Guardar áreas adicionales en user_area_assignments
                from apps.users.models import UserAreaAssignment
                for aid in area_ids:
                    try:
                        area_obj = Area.objects.get(areaId=aid)
                        UserAreaAssignment.objects.get_or_create(user=new_user, area=area_obj)
                    except Area.DoesNotExist:
                        pass

                messages.success(request, f"Usuario '{new_user.email}' creado correctamente.")
                return redirect('admin_panel:usuarios')
            except Exception as e:
                messages.error(request, f'Error: {e}')

    return render(request, 'admin_panel/users/form.html', {
        'accion':        'Crear',
        'areas':         areas,
        'roles':         roles,
        'es_superadmin': is_superadmin(user),
    })


@panel_required
def userAdminEditView(request, pk):
    usuario = get_object_or_404(User, userId=pk)
    user    = request.user

    # Admins de área nunca pueden editar superadmins
    if not is_superadmin(user) and is_superadmin(usuario):
        messages.error(request, 'No tienes permiso para editar a un super administrador.')
        return redirect('admin_panel:usuarios')

    # Verificar que este admin tiene permiso sobre el área del usuario a editar
    if not is_superadmin(user):
        allowed = get_allowed_area_names(user)
        if usuario.area.areaName not in allowed:
            messages.error(request, 'No tienes permiso para editar usuarios de esa área.')
            return redirect('admin_panel:usuarios')

    if is_superadmin(user):
        areas = Area.objects.all()
        roles = Role.objects.all()
    else:
        allowed = get_allowed_area_names(user)
        areas   = Area.objects.filter(areaName__in=allowed)
        creatable_role_names = get_creatable_agent_role_names(user)
        roles = Role.objects.filter(roleName__in=creatable_role_names)

    # Áreas actualmente asignadas al usuario
    from apps.users.models import UserAreaAssignment
    usuario_area_ids = list(
        UserAreaAssignment.objects.filter(user=usuario).values_list('area__areaId', flat=True)
    )
    # Si no tiene asignaciones en la tabla intermedia, usar el área FK como default
    if not usuario_area_ids and usuario.area_id:
        usuario_area_ids = [usuario.area_id]

    if request.method == 'POST':
        usuario.name     = request.POST.get('name', '').strip()
        usuario.lastname = request.POST.get('lastname', '').strip()
        usuario.email    = request.POST.get('email', '').strip()
        usuario.status   = request.POST.get('status', 'activo')

        # is_staff / is_superuser solo los puede modificar el super admin
        if is_superadmin(user):
            usuario.is_staff     = request.POST.get('is_staff') == 'on'
            usuario.is_superuser = request.POST.get('is_superuser') == 'on'

        area_ids = request.POST.getlist('areas')
        if not area_ids:
            messages.error(request, 'Debes seleccionar al menos un área.')
            return render(request, 'admin_panel/users/form.html', {
                'accion': 'Editar', 'areas': areas, 'roles': roles,
                'usuario': usuario, 'es_superadmin': is_superadmin(user),
                'usuario_area_ids': usuario_area_ids,
            })

        try:
            # Rol
            usuario.role = Role.objects.get(roleId=request.POST.get('role'))

            # Área principal (primera seleccionada)
            nueva_area = Area.objects.get(areaId=area_ids[0])
            if not is_superadmin(user) and nueva_area.areaName not in get_allowed_area_names(user):
                messages.error(request, 'No puedes mover usuarios a un área que no gestionas.')
                return render(request, 'admin_panel/users/form.html', {
                    'accion': 'Editar', 'areas': areas, 'roles': roles,
                    'usuario': usuario, 'es_superadmin': is_superadmin(user),
                    'usuario_area_ids': usuario_area_ids,
                })
            usuario.area = nueva_area
        except Exception:
            messages.error(request, 'Rol o área no válidos.')
            return render(request, 'admin_panel/users/form.html', {
                'accion': 'Editar', 'areas': areas, 'roles': roles,
                'usuario': usuario, 'es_superadmin': is_superadmin(user),
                'usuario_area_ids': usuario_area_ids,
            })

        new_password = request.POST.get('password', '').strip()
        if new_password:
            if len(new_password) < 6:
                messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
                return render(request, 'admin_panel/users/form.html', {
                    'accion': 'Editar', 'areas': areas, 'roles': roles,
                    'usuario': usuario, 'es_superadmin': is_superadmin(user),
                    'usuario_area_ids': usuario_area_ids,
                })
            usuario.set_password(new_password)

        usuario.save()

        # Actualizar asignaciones de áreas
        UserAreaAssignment.objects.filter(user=usuario).delete()
        for aid in area_ids:
            try:
                area_obj = Area.objects.get(areaId=aid)
                UserAreaAssignment.objects.get_or_create(user=usuario, area=area_obj)
            except Area.DoesNotExist:
                pass

        messages.success(request, 'Usuario actualizado.')
        return redirect('admin_panel:usuarios')

    return render(request, 'admin_panel/users/form.html', {
        'accion':          'Editar',
        'areas':           areas,
        'roles':           roles,
        'usuario':         usuario,
        'es_superadmin':   is_superadmin(user),
        'usuario_area_ids': usuario_area_ids,
    })


@panel_required
def userAdminDeleteView(request, pk):
    usuario = get_object_or_404(User, userId=pk)
    user    = request.user
    target_is_superadmin = is_superadmin(usuario)

    # ── Nadie puede eliminarse a sí mismo ────────────────────────────────────
    if user.userId == pk:
        messages.error(request, 'No puedes eliminar tu propio usuario.')
        return redirect('admin_panel:usuarios')

    # ── Solo un super admin puede eliminar a otro super admin ─────────────────
    if target_is_superadmin and not is_superadmin(user):
        messages.error(request, 'No tienes permiso para eliminar un super administrador.')
        return redirect('admin_panel:usuarios')

    # ── Admin de área: solo puede eliminar usuarios de sus áreas ─────────────
    if not is_superadmin(user):
        allowed = get_allowed_area_names(user)
        if usuario.area.areaName not in allowed:
            messages.error(request, 'No tienes permiso para eliminar usuarios de esa área.')
            return redirect('admin_panel:usuarios')

    if request.method == 'POST':
        # ── Contraseña maestra obligatoria para eliminar super admins ─────────
        if target_is_superadmin:
            master_pw = request.POST.get('master_password', '')
            if master_pw != SUPERADMIN_MASTER_PASSWORD:
                messages.error(request, 'Contraseña maestra incorrecta. El super administrador no fue eliminado.')
                return render(request, 'admin_panel/confirm_delete_superadmin.html', {
                    'objeto': f'{usuario.name} {usuario.lastname} ({usuario.email})',
                    'usuario_pk': pk,
                })

        nombre = usuario.email
        usuario.delete()
        messages.success(request, f"Usuario '{nombre}' eliminado.")
        return redirect('admin_panel:usuarios')

    # Template especial si el objetivo es super admin (pide contraseña maestra)
    if target_is_superadmin:
        return render(request, 'admin_panel/confirm_delete_superadmin.html', {
            'objeto': f'{usuario.name} {usuario.lastname} ({usuario.email})',
            'usuario_pk': pk,
        })

    return render(request, 'admin_panel/confirm_delete.html', {
        'objeto': f'{usuario.name} {usuario.lastname} ({usuario.email})',
        'tipo': 'Usuario', 'cancel_url': 'admin_panel:usuarios'
    })




# ══════════════════════════════════════════════════════════════════════════════
# REPORTERÍA
# ══════════════════════════════════════════════════════════════════════════════

@panel_required
def reportesView(request):
    """
    Reporte centralizado para super admins y admins de área.
    Super admin → datos globales de todo el sistema.
    Admin de área → datos filtrados por sus áreas.
    """
    from django.db.models import Count, Avg, F, ExpressionWrapper, DurationField, Q
    from django.db.models.functions import TruncDate, TruncMonth
    from datetime import datetime, timedelta, date
    import json

    user = request.user

    # ── Rango de fechas del filtro ────────────────────────────────────────────
    # Usar datetime.now() en lugar de timezone.now() porque USE_TZ=False
    hoy       = datetime.now().date()
    default_desde = hoy - timedelta(days=29)
    desde_str = request.GET.get('desde', default_desde.isoformat())
    hasta_str = request.GET.get('hasta', hoy.isoformat())

    try:
        desde = date.fromisoformat(desde_str)
        hasta = date.fromisoformat(hasta_str)
    except ValueError:
        desde = default_desde
        hasta = hoy

    # ── Base queryset según rol ───────────────────────────────────────────────
    if is_superadmin(user):
        qs_all  = Ticket.objects.all()
        areas_qs = Area.objects.all()
    else:
        allowed  = get_allowed_area_names(user)
        qs_all   = Ticket.objects.filter(area__areaName__in=allowed)
        areas_qs = Area.objects.filter(areaName__in=allowed)

    qs_rango = qs_all.filter(
        createdAt__date__gte=desde,
        createdAt__date__lte=hasta,
    )

    # ── KPIs globales (del rango) ─────────────────────────────────────────────
    total       = qs_rango.count()
    abiertos    = qs_rango.filter(status='abierto').count()
    en_proceso  = qs_rango.filter(status='en_proceso').count()
    pendientes  = qs_rango.filter(status='pendiente').count()
    en_espera   = qs_rango.filter(status='en_espera').count()
    escalados   = qs_rango.filter(status='escalado').count()
    resueltos   = qs_rango.filter(status='resuelto').count()
    cerrados    = qs_rango.filter(status='cerrado').count()

    # Tiempo promedio de resolución en horas (tickets cerrados o resueltos con closedAt)
    cerrados_con_fecha = qs_rango.filter(
        status__in=('cerrado', 'resuelto'), closedAt__isnull=False
    ).annotate(
        duracion=ExpressionWrapper(
            F('closedAt') - F('createdAt'), output_field=DurationField()
        )
    )
    tiempo_promedio = None
    if cerrados_con_fecha.exists():
        total_segundos = sum(
            t.duracion.total_seconds()
            for t in cerrados_con_fecha
            if t.duracion is not None
        )
        promedio_seg   = total_segundos / cerrados_con_fecha.count()
        tiempo_promedio = round(promedio_seg / 3600, 1)  # en horas

    # ── Tickets por día (para gráfica de línea) ───────────────────────────────
    por_dia = (
        qs_rango
        .annotate(dia=TruncDate('createdAt', tzinfo=None))
        .values('dia')
        .annotate(total=Count('ticketId'))
        .order_by('dia')
    )
    dias_labels  = [str(r['dia']) for r in por_dia]
    dias_valores = [r['total'] for r in por_dia]

    # ── Tickets por área ──────────────────────────────────────────────────────
    por_area = (
        qs_rango
        .values('area__areaName')
        .annotate(total=Count('ticketId'))
        .order_by('-total')
    )
    areas_labels  = [r['area__areaName'] for r in por_area]
    areas_valores = [r['total'] for r in por_area]

    # ── Tickets por prioridad ─────────────────────────────────────────────────
    por_prioridad = (
        qs_rango
        .values('priority')
        .annotate(total=Count('ticketId'))
        .order_by('priority')
    )
    PRIORITY_LABELS = {
        'baja': 'Baja', 'media': 'Media', 'alta': 'Alta', 'critica': 'Crítica'
    }
    prioridad_labels  = [PRIORITY_LABELS.get(r['priority'], r['priority']) for r in por_prioridad]
    prioridad_valores = [r['total'] for r in por_prioridad]

    # ── Tickets por categoría (top 10) ────────────────────────────────────────
    por_categoria = (
        qs_rango
        .values('category__categoryName', 'area__areaName')
        .annotate(total=Count('ticketId'))
        .order_by('-total')[:10]
    )

    # ── Rendimiento de agentes ────────────────────────────────────────────────
    from apps.users.models import User as UserModel
    from apps.core.permissions import AGENT_ROLE_MAP

    if is_superadmin(user):
        agentes_qs = UserModel.objects.filter(role__roleName__in=AGENT_ROLE_MAP.keys())
    else:
        allowed = get_allowed_area_names(user)
        agentes_qs = UserModel.objects.filter(
            role__roleName__in=AGENT_ROLE_MAP.keys(),
            area__areaName__in=allowed
        )

    rendimiento_agentes = []
    for agente in agentes_qs.select_related('area', 'role'):
        tickets_asignados = qs_rango.filter(assignedTo=agente)
        rendimiento_agentes.append({
            'agente':    f"{agente.name} {agente.lastname}",
            'area':      agente.area.areaName if agente.area_id else '—',
            'rol':       agente.role.roleName if agente.role_id else '—',
            'asignados': tickets_asignados.count(),
            'resueltos': tickets_asignados.filter(status__in=('cerrado', 'resuelto')).count(),
            'abiertos':  tickets_asignados.filter(status='abierto').count(),
            'en_proceso':tickets_asignados.filter(status='en_proceso').count(),
            'escalados': tickets_asignados.filter(status='escalado').count(),
        })
    rendimiento_agentes.sort(key=lambda x: x['resueltos'], reverse=True)

    # ── Tendencia mensual (últimos 6 meses, independiente del filtro) ─────────
    hace_6_meses = datetime.now() - timedelta(days=180)
    tendencia_mensual = (
        qs_all
        .filter(createdAt__gte=hace_6_meses)
        .annotate(mes=TruncMonth('createdAt', tzinfo=None))
        .values('mes')
        .annotate(
            creados=Count('ticketId'),
            cerrados_mes=Count('ticketId', filter=Q(status='cerrado')),
        )
        .order_by('mes')
    )
    meses_labels     = [r['mes'].strftime('%b %Y') for r in tendencia_mensual]
    meses_creados    = [r['creados'] for r in tendencia_mensual]
    meses_cerrados   = [r['cerrados_mes'] for r in tendencia_mensual]

    context = {
        # Filtros
        'desde': desde.isoformat(),
        'hasta': hasta.isoformat(),
        # KPIs
        'total':          total,
        'abiertos':       abiertos,
        'en_proceso':     en_proceso,
        'pendientes':     pendientes,
        'en_espera':      en_espera,
        'escalados':      escalados,
        'resueltos':      resueltos,
        'cerrados':       cerrados,
        'tiempo_promedio': tiempo_promedio,
        # Gráficas (JSON)
        'dias_labels':       json.dumps(dias_labels),
        'dias_valores':      json.dumps(dias_valores),
        'areas_labels':      json.dumps(areas_labels),
        'areas_valores':     json.dumps(areas_valores),
        'prioridad_labels':  json.dumps(prioridad_labels),
        'prioridad_valores': json.dumps(prioridad_valores),
        'meses_labels':      json.dumps(meses_labels),
        'meses_creados':     json.dumps(meses_creados),
        'meses_cerrados':    json.dumps(meses_cerrados),
        # Tablas
        'por_categoria':       por_categoria,
        'rendimiento_agentes': rendimiento_agentes,
        # Flags
        'es_superadmin': is_superadmin(user),
        'areas_scope':   list(areas_qs.values_list('areaName', flat=True)),
    }
    return render(request, 'admin_panel/reportes.html', context)

# ══════════════════════════════════════════════════════════════════════════════
# DEBUG: diagnóstico de permisos de un usuario  (quitar en producción)
# Acceso: /panel/debug/<pk>/
# ══════════════════════════════════════════════════════════════════════════════
@superadmin_required
def debugPermissionsView(request, pk):
    from apps.core.permissions import (
        AREA_ADMIN_ROLE_MAP, AGENT_ROLE_MAP, SUPERADMIN_ROLE_NAMES,
        is_superadmin, is_area_admin, is_agent, get_allowed_area_names,
    )
    from django.http import HttpResponse

    usuario = get_object_or_404(User, userId=pk)
    role_name = usuario.role.roleName if usuario.role_id else '(sin rol)'
    area_name = usuario.area.areaName if usuario.area_id else '(sin área)'

    lines = [
        f"<h2>Debug permisos: {usuario.username}</h2>",
        f"<b>Rol en BD:</b> '{role_name}'",
        f"<b>Área FK en BD:</b> '{area_name}'",
        f"<b>is_superuser:</b> {usuario.is_superuser}",
        f"<b>is_staff:</b> {usuario.is_staff}",
        "<hr>",
        f"<b>is_superadmin():</b> {is_superadmin(usuario)}",
        f"<b>is_area_admin():</b> {is_area_admin(usuario)}",
        f"<b>is_agent():</b> {is_agent(usuario)}",
        "<hr>",
        f"<b>Rol en SUPERADMIN_ROLE_NAMES:</b> {role_name in SUPERADMIN_ROLE_NAMES}",
        f"<b>Rol en AREA_ADMIN_ROLE_MAP:</b> {role_name in AREA_ADMIN_ROLE_MAP}",
        f"<b>Rol en AGENT_ROLE_MAP:</b> {role_name in AGENT_ROLE_MAP}",
        "<hr>",
        f"<b>get_allowed_area_names():</b> {get_allowed_area_names(usuario)}",
        "<hr>",
        "<b>Claves exactas en AREA_ADMIN_ROLE_MAP:</b><ul>",
    ]
    for key, areas in AREA_ADMIN_ROLE_MAP.items():
        match = (key == role_name)
        lines.append(f"<li>'{key}' → {areas} — <b>{'✅ MATCH' if match else '❌ no match'}</b></li>")
    lines.append("</ul>")
    lines.append(f"<br><a href='/panel/usuarios/'>← Volver</a>")

    return HttpResponse("<br>".join(lines))
