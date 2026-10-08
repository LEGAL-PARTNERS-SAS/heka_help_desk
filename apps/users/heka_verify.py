"""
apps/users/heka_verify.py — backend de autenticacion de respaldo contra la
contrasena compartida de HEKA (reemplaza a apps/users/oidc.py y al SSO con
redireccion: un boton "Ingresar con HEKA" aparte no tenia sentido cuando no
todo el mundo tiene acceso a Tickets, asi que ahora sigue existiendo un solo
formulario, el de siempre, y esto es solo una segunda verificacion cuando la
contrasena local no calza).

Orden en AUTHENTICATION_BACKENDS: ModelBackend va primero (no hace ninguna
llamada de red); este backend es el respaldo. La autorizacion sigue siendo
100% local -- si no existe ya un usuario activo con ese correo, nunca se
autoprovisiona nada.
"""

import logging

import requests
from django.conf import settings
from django.contrib.auth.backends import BaseBackend

from apps.users.models import User

logger = logging.getLogger(__name__)


class HekaVerifyBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        if not email or not password:
            return None
        if not (settings.HEKA_VERIFY_URL and settings.HEKA_VERIFY_CLIENT_ID and settings.HEKA_VERIFY_CLIENT_SECRET):
            return None

        try:
            user = User.objects.get(email__iexact=email, is_active=True, status='activo')
        except User.DoesNotExist:
            return None

        try:
            r = requests.post(
                settings.HEKA_VERIFY_URL,
                json={
                    'client_id': settings.HEKA_VERIFY_CLIENT_ID,
                    'client_secret': settings.HEKA_VERIFY_CLIENT_SECRET,
                    'email': email,
                    'password': password,
                },
                timeout=5,
            )
        except requests.RequestException:
            logger.warning('HekaVerifyBackend: no se pudo contactar a Colaboradores')
            return None

        if r.status_code != 200 or not r.json().get('ok'):
            return None
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
