"""
config/settings/development.py — versión segura
"""
from .base import *  # noqa

DEBUG = True

# ── CORS: solo el frontend local, NUNCA allow_all ────────────────────────────
ALLOWED_HOSTS = [
    "13.222.14.227",
    "localhost",
    "127.0.0.1",
    "soporte.heka.com.ec"
]

CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS   = ['http://localhost:3000', 'http://127.0.0.1:3000']

# ── Las cookies Secure solo funcionan en HTTPS.
#    En dev usamos HTTP, así que las deshabilitamos aquí.
#    En producción (production.py) siempre van en True. ─────────────────────
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE    = False

# ── Herramienta de debug SQL (opcional, descomenta si la instalas) ────────────
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
# INTERNAL_IPS = ['127.0.0.1']

# ── Email: forzar SMTP real (nunca consola en dev con MFA) ───────────────────
import environ as _environ
_env = _environ.Env()
_environ.Env.read_env()          # re-lee el .env desde el directorio actual

EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = _env('EMAIL_HOST',          default='smtp.office365.com')
EMAIL_PORT          = _env.int('EMAIL_PORT',       default=587)
EMAIL_HOST_USER     = _env('EMAIL_HOST_USER',      default='soporte@heka.com.ec')
EMAIL_HOST_PASSWORD = _env('EMAIL_HOST_PASSWORD',  default='H3k4-Ant0n10.')
EMAIL_USE_TLS       = _env.bool('EMAIL_USE_TLS',   default=True)
EMAIL_USE_SSL       = _env.bool('EMAIL_USE_SSL',   default=False)
EMAIL_TIMEOUT       = 15
DEFAULT_FROM_EMAIL  = _env('EMAIL_HOST_USER',      default='')

CSRF_TRUSTED_ORIGINS = [
    "https://soporte.heka.com.ec",
    "http://soporte.heka.com.ec"
]