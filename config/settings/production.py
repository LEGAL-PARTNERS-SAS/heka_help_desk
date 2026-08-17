"""
config/settings/production.py — versión segura
"""
from .base import *  # noqa

DEBUG = False

ALLOWED_HOSTS = [
    "soporte.heka.com.ec",
    "127.0.0.1",
    "localhost",
    "13.222.14.227",
    "ec2-13-222-14-227.compute-1.amazonaws.com"
]

# ── HTTPS ─────────────────────────────────────────────────────────────────────
SECURE_SSL_REDIRECT             = True
SECURE_PROXY_SSL_HEADER         = ('HTTP_X_FORWARDED_PROTO', 'https')

# ── Cookies seguras ───────────────────────────────────────────────────────────
SESSION_COOKIE_SECURE           = True   # cookie solo viaja por HTTPS
CSRF_COOKIE_SECURE              = True   # idem para CSRF

# ── HSTS: fuerza HTTPS por 1 año ──────────────────────────────────────────────
SECURE_HSTS_SECONDS             = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS  = True
SECURE_HSTS_PRELOAD             = True

# ── Cache en producción: usar Redis si está disponible ────────────────────────
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#         'LOCATION': env('REDIS_URL', default='redis://localhost:6379/1'),
#     }
# }
