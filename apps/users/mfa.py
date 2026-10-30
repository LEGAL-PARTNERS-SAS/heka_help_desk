"""
apps/users/mfa.py
=================
Lógica de MFA por email: genera, envía y valida códigos de 6 dígitos
que expiran a los 5 minutos. Se usa la tabla `mfa_codes` en la BD.
"""

import random
import string
from datetime import datetime, timedelta

from django.conf import settings
from django.db import connection

from apps.core.emails import TEMAS, render_shell, send_html_mail


# ─── Helpers de BD (raw SQL porque la tabla es managed=False) ─────────────────

def _now():
    return datetime.now()


def _create_code(user_id: int) -> str:
    """Invalida códigos anteriores del usuario y crea uno nuevo."""
    code = ''.join(random.choices(string.digits, k=6))
    expires_at = _now() + timedelta(minutes=5)

    with connection.cursor() as cur:
        # Invalidar anteriores
        cur.execute(
            "UPDATE mfa_codes SET used = 1 WHERE user_id = %s AND used = 0",
            [user_id]
        )
        # Insertar nuevo
        cur.execute(
            "INSERT INTO mfa_codes (user_id, code, expires_at, used) VALUES (%s, %s, %s, 0)",
            [user_id, code, expires_at]
        )
    return code


def _verify_code(user_id: int, code: str) -> tuple[bool, str]:
    """
    Valida el código. Devuelve (True, '') si es válido,
    o (False, 'mensaje de error') si no.
    """
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT id, expires_at, used
            FROM mfa_codes
            WHERE user_id = %s AND code = %s
            ORDER BY created_at DESC
            LIMIT 1
            """,
            [user_id, code]
        )
        row = cur.fetchone()

    if not row:
        return False, 'Código incorrecto. Verifica el correo.'

    mfa_id, expires_at, used = row

    if used:
        return False, 'Este código ya fue utilizado. Solicita uno nuevo.'

    if _now() > expires_at:
        return False, 'El código ha expirado (máx. 5 minutos). Solicita uno nuevo.'

    # Marcar como usado
    with connection.cursor() as cur:
        cur.execute("UPDATE mfa_codes SET used = 1 WHERE id = %s", [mfa_id])

    return True, ''


# ─── API pública ──────────────────────────────────────────────────────────────

def send_mfa_code(user) -> bool:
    """
    Genera un código, lo guarda en BD y lo envía al correo del usuario.
    Devuelve True si el correo se envió, False si hubo error.
    """
    code = _create_code(user.pk)

    saludo = f'Hola{" " + user.name if user.name else ""}'
    plain_fallback = (
        f'{saludo},\n\n'
        f'Tu código de verificación de Heka es:\n\n'
        f'    {code}\n\n'
        f'Este código es válido por 5 minutos.\n'
        f'Si no intentaste ingresar, ignora este mensaje.\n\n'
        f'— Equipo Heka'
    )

    html_body = render_shell(
        eyebrow='Verificación en dos pasos',
        titulo='Tu código de acceso',
        intro_html=f'{saludo}, usa este código para completar tu inicio de sesión. Es válido por 5 minutos.',
        detalle=[('Código', code)],
        app_nombre='Tickets',
        **TEMAS['azul'],
    )

    try:
        return send_html_mail(
            to=user.email,
            subject='Tu código de verificación — Heka',
            html_body=html_body,
            plain_fallback=plain_fallback,
        )
    except Exception as e:
        import traceback
        print('Error enviando correo:', e)
        traceback.print_exc()
        return False


def verify_mfa_code(user, code: str) -> tuple[bool, str]:
    """Valida el código ingresado por el usuario."""
    return _verify_code(user.pk, code.strip())
