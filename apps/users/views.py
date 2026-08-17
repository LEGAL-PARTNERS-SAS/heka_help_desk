"""
apps/users/views.py — autenticación por EMAIL con MFA de 6 dígitos
"""

import re
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def _get_client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


def _log(request, user, action):
    try:
        from apps.audit.models import AuditLog
        AuditLog.registrar(
            user=user, action=action, tableName='users',
            recordId=user.pk if user else None,
            ipAddress=_get_client_ip(request),
        )
    except Exception:
        pass


# ─── Login (paso 1: email + contraseña) ──────────────────────────────────────

def loginView(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard')

    error = None
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, email=email, password=password)
        if user is not None:
            if not user.is_active:
                error = 'Tu cuenta está inactiva. Contacta al administrador.'
                _log(request, user, f'LOGIN_INACTIVE: "{email}"')
            else:
                # ── Credenciales OK → enviar código MFA ──────────────────────
                from apps.users.mfa import send_mfa_code
                enviado = send_mfa_code(user)

                # Guardar el user_id en sesión para el paso 2
                request.session['mfa_user_id'] = user.pk
                request.session['mfa_next']    = (
                    request.GET.get('next') or request.POST.get('next', '')
                )

                if enviado:
                    return redirect('users:mfa_verify')
                else:
                    # Si el correo falla, logear igual pero avisar
                    error = 'No se pudo enviar el código. Revisa la configuración de correo.'
                    _log(request, user, f'MFA_SEND_FAIL: "{email}"')
        else:
            error = 'Correo o contraseña incorrectos.'
            _log(request, None, f'LOGIN_FAIL: intento para "{email}"')

    return render(request, 'users/login.html', {'error': error})


# ─── MFA (paso 2: código de 6 dígitos) ───────────────────────────────────────

def mfaVerifyView(request):
    """Pide el código que llegó al correo y completa el login."""
    user_id = request.session.get('mfa_user_id')
    if not user_id:
        return redirect('users:login')

    from apps.users.models import User
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('users:login')

    error = None

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # Reenviar código
        if action == 'reenviar':
            from apps.users.mfa import send_mfa_code
            if send_mfa_code(user):
                messages.success(request, 'Se envió un nuevo código a tu correo.')
            else:
                messages.error(request, 'No se pudo reenviar el código.')
            return redirect('users:mfa_verify')

        # Verificar código
        code = request.POST.get('code', '').strip()
        from apps.users.mfa import verify_mfa_code
        valid, msg = verify_mfa_code(user, code)

        if valid:
            # Limpiar sesión MFA y hacer login real
            next_url = request.session.pop('mfa_next', '')
            request.session.pop('mfa_user_id', None)
            request.session.cycle_key()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            _log(request, user, f'LOGIN_OK (MFA): "{user.email}"')
            if next_url and next_url.startswith('/') and not next_url.startswith('//'):
                return redirect(next_url)
            return redirect('core:dashboard')
        else:
            error = msg
            _log(request, user, f'MFA_FAIL: "{user.email}" — {msg}')

    # Mostrar solo los últimos 3 caracteres del email (privacidad)
    email_masked = _mask_email(user.email)
    return render(request, 'users/mfa_verify.html', {
        'email_masked': email_masked,
        'error':        error,
    })


def _mask_email(email: str) -> str:
    """correo@empresa.com → cor***@empresa.com"""
    try:
        local, domain = email.split('@', 1)
        visible = local[:3] if len(local) >= 3 else local[:1]
        return f'{visible}***@{domain}'
    except Exception:
        return email


# ─── Logout ───────────────────────────────────────────────────────────────────

def logoutView(request):
    user = request.user
    if user.is_authenticated:
        _log(request, user, f'LOGOUT: "{user.email}"')
    logout(request)
    return redirect('users:login')


# ─── Perfil ───────────────────────────────────────────────────────────────────

@login_required
def profileView(request):
    return render(request, 'users/profile.html')


@login_required
def userListView(request):
    return render(request, 'users/list.html')


# ─── Registro público (email + contraseña) ────────────────────────────────────

def registerView(request):
    from apps.users.models import User
    from apps.core.models import Role, Area

    errors    = {}
    form_data = {}

    if request.method == 'POST':
        email     = request.POST.get('email', '').strip()
        password  = request.POST.get('password', '')
        password2 = request.POST.get('password2', '')

        form_data = {'email': email}

        if not email:
            errors['email'] = 'El correo es obligatorio.'
        elif not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            errors['email'] = 'Ingresa un correo válido.'
        elif User.objects.filter(email=email).exists():
            errors['email'] = 'Ya existe una cuenta con ese correo.'

        if not password or len(password) < 8:
            errors['password'] = 'Mínimo 8 caracteres.'
        elif not re.search(r'[A-Z]', password):
            errors['password'] = 'Debe contener al menos una mayúscula.'
        elif not re.search(r'\d', password):
            errors['password'] = 'Debe contener al menos un número.'

        if password and password != password2:
            errors['password2'] = 'Las contraseñas no coinciden.'

        if not errors:
            try:
                role = Role.objects.get(roleName='Usuario')
                area = Area.objects.first()
                if area is None:
                    area, _ = Area.objects.get_or_create(areaName='General')

                user = User.objects.createUser(
                    email=email, password=password,
                    role=role, area=area,
                    is_staff=False, is_superuser=False,
                )
                _log(request, user, f'REGISTER: nueva cuenta "{email}"')
                messages.success(request, 'Cuenta creada correctamente. Ya puedes ingresar.')
                return redirect('users:login')

            except Role.DoesNotExist:
                errors['general'] = 'Error: no existe el rol "Usuario". Contacta al administrador.'
            except Exception as e:
                errors['general'] = f'Error al crear la cuenta: {str(e)}'

    return render(request, 'users/register.html', {'errors': errors, 'form_data': form_data})
