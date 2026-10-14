"""
apps/users/heka_sync.py — sincronizacion hacia adelante de la contraseña
compartida de HEKA (sentido inverso de heka_verify.py): cuando un admin fija
o cambia la contraseña de alguien ACA, se la manda tambien a Colaboradores
para que quede como la compartida. Mejor esfuerzo: si Colaboradores no esta
configurado o no responde, nunca rompe el guardado local de la contraseña.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def sincronizar_password_compartida(email: str, password: str) -> None:
    if not (settings.HEKA_SYNC_PASSWORD_URL and settings.HEKA_VERIFY_CLIENT_ID and settings.HEKA_VERIFY_CLIENT_SECRET):
        return
    try:
        requests.post(
            settings.HEKA_SYNC_PASSWORD_URL,
            json={
                'client_id': settings.HEKA_VERIFY_CLIENT_ID,
                'client_secret': settings.HEKA_VERIFY_CLIENT_SECRET,
                'email': email,
                'password': password,
            },
            timeout=5,
        )
    except requests.RequestException:
        logger.warning('sincronizar_password_compartida: no se pudo contactar a Colaboradores')
