"""
apps/users/middleware.py
========================
Middleware de seguridad para Heka:

1. RateLimitLoginMiddleware
   - Bloquea por IP y por username después de N intentos fallidos.
   - Usa la sesión de Django para contar (no requiere Redis).
   - Si se supera el límite → 429 con tiempo de espera.

2. SecurityHeadersMiddleware
   - Agrega cabeceras HTTP de seguridad en cada respuesta.
   - Content-Security-Policy, X-Frame-Options, etc.
"""

import time
from django.http import HttpResponse
from django.utils.decorators import sync_only_middleware


# ── Configuración ─────────────────────────────────────────────────────────────

MAX_ATTEMPTS    = 5          # intentos antes de bloquear
LOCKOUT_SECONDS = 5 * 60     # 5 minutos de bloqueo
LOGIN_URL_PATH  = '/usuarios/login/'


class RateLimitLoginMiddleware:
    """
    Bloquea IPs y usernames después de MAX_ATTEMPTS intentos fallidos.
    Estado guardado en la cache de Django (usa LocMemCache por defecto).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Solo actuar en POST al login
        if request.method == 'POST' and request.path == LOGIN_URL_PATH:
            block_response = self._check_rate_limit(request)
            if block_response:
                return block_response

        response = self.get_response(request)

        # Post-proceso: registrar intento fallido si el login fracasó
        if (
            request.method == 'POST'
            and request.path == LOGIN_URL_PATH
            and response.status_code in (200, 302)
        ):
            # Login fallido: Django vuelve 200 (muestra error) en vez de 302 (redirect)
            if response.status_code == 200:
                self._record_failure(request)
            else:
                # Login exitoso: limpiar contadores
                self._clear_counters(request)

        return response

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '0.0.0.0')

    def _ip_key(self, ip):
        return f'heka_login_ip_{ip}'

    def _user_key(self, email):
        return f'heka_login_email_{email}'

    def _check_rate_limit(self, request):
        from django.core.cache import cache

        ip    = self._get_ip(request)
        email = request.POST.get('email', '')

        for key in [self._ip_key(ip), self._user_key(email)]:
            data = cache.get(key)
            if data and data['attempts'] >= MAX_ATTEMPTS:
                wait = int(LOCKOUT_SECONDS - (time.time() - data['first_attempt']))
                if wait > 0:
                    mins = wait // 60
                    segs = wait % 60
                    msg = (
                        f'Demasiados intentos fallidos. '
                        f'Intenta de nuevo en {mins}m {segs}s.'
                    )
                    request.session['login_lockout_msg'] = msg
                    from django.shortcuts import render
                    return render(request, 'users/login.html', {
                        'error': msg,
                        'locked': True,
                    }, status=429)
                else:
                    cache.delete(key)
        return None

    def _record_failure(self, request):
        from django.core.cache import cache

        ip    = self._get_ip(request)
        email = request.POST.get('email', '')

        for key in [self._ip_key(ip), self._user_key(email)]:
            data = cache.get(key) or {'attempts': 0, 'first_attempt': time.time()}
            data['attempts'] += 1
            cache.set(key, data, timeout=LOCKOUT_SECONDS)

    def _clear_counters(self, request):
        from django.core.cache import cache

        ip    = self._get_ip(request)
        email = request.POST.get('email', '')
        cache.delete(self._ip_key(ip))
        cache.delete(self._user_key(email))


class SecurityHeadersMiddleware:
    """
    Agrega cabeceras HTTP de seguridad en todas las respuestas.
    Complementa las de Django SecurityMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Evitar que el navegador adivine el tipo de contenido
        response['X-Content-Type-Options'] = 'nosniff'

        # Evitar clickjacking (también lo hace XFrameOptionsMiddleware, doble capa)
        response['X-Frame-Options'] = 'DENY'

        # Referrer: no enviar la URL completa a sitios externos
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        # Permisos del navegador: deshabilitar funciones no necesarias
        response['Permissions-Policy'] = (
            'geolocation=(), camera=(), microphone=(), '
            'payment=(), usb=(), interest-cohort=()'
        )

        # Content-Security-Policy
        # Permite: recursos propios, Google Fonts, jQuery CDN (con SRI), jsDelivr
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' "
                "https://code.jquery.com "
                "https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' "
                "https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Eliminar cabecera que revela el servidor
        if 'Server' in response:
            del response['Server']
        if 'X-Powered-By' in response:
            del response['X-Powered-By']

        return response
