import os
import environ
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ── Logging ───────────────────────────────────────────────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(str(BASE_DIR), 'logs', 'django.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
    },
}

# ── Auth redirects ────────────────────────────────────────────────────────────
LOGIN_URL           = '/usuarios/login/'
LOGIN_REDIRECT_URL  = '/tickets/'          # ← CORREGIDO: era '/', ahora va a Django
LOGOUT_REDIRECT_URL = '/usuarios/login/'

# ¡AÑADE ESTAS DOS LÍNEAS AQUÍ!
APPEND_SLASH = True
PREPEND_WWW  = False

# ── Entorno ───────────────────────────────────────────────────────────────────
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(str(BASE_DIR / '.env'))

SECRET_KEY    = env('SECRET_KEY')
DEBUG         = env('DEBUG')
ALLOWED_HOSTS = ['soporte.heka.com.ec', 'localhost', '127.0.0.1', '13.222.14.227']

# ── Apps ──────────────────────────────────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_celery_beat',
    'django_celery_results',
]

LOCAL_APPS = [
    'apps.core.apps.CoreConfig',
    'apps.users.apps.UsersConfig',
    'apps.tickets.apps.TicketsConfig',
    'apps.audit.apps.AuditConfig',
    'apps.admin_panel',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #'apps.users.middleware.RateLimitLoginMiddleware',
    'apps.users.middleware.SecurityHeadersMiddleware',
]

ROOT_URLCONF     = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ── Base de datos ─────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.mysql',
        'NAME':     env('DB_NAME',     default='helpdesk_db'),
        'USER':     env('DB_USER',     default='root'),
        'PASSWORD': env('DB_PASSWORD', default=''),
        'HOST':     env('DB_HOST',     default='localhost'),
        'PORT':     env('DB_PORT',     default='3306'),
        'OPTIONS': {
            'charset':      'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'ssl_disabled': env.bool('DB_SSL_DISABLED', default=True),
        },
        'CONN_MAX_AGE': 60,
    }
}

AUTH_USER_MODEL = 'users.User'

# ── Contraseña compartida de HEKA (heka-colaboradores como fuente) ─────────────
# El login con contraseña propia + MFA sigue viviendo en apps/users; esto
# agrega un backend de respaldo (ModelBackend va primero, nunca se reemplaza)
# para que la misma contraseña compartida de HEKA también funcione acá si la
# local no calza. Ver apps/users/heka_verify.py -- la identidad y la
# autorización siguen siendo 100% locales, nunca se autoprovisiona nada.
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'apps.users.heka_verify.HekaVerifyBackend',
]
HEKA_VERIFY_URL = 'https://soporte.heka.com.ec/colaboradores/api/verify'
HEKA_VERIFY_CLIENT_ID = env('HEKA_VERIFY_CLIENT_ID', default='')
HEKA_VERIFY_CLIENT_SECRET = env('HEKA_VERIFY_CLIENT_SECRET', default='')
LOGIN_REDIRECT_URL_FAILURE = '/usuarios/login/'

# ── Contraseñas ───────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Sesión ────────────────────────────────────────────────────────────────────
SESSION_ENGINE               = 'django.contrib.sessions.backends.db'
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE           = 3600
SESSION_SAVE_EVERY_REQUEST   = True
SESSION_COOKIE_HTTPONLY      = True
SESSION_COOKIE_SAMESITE      = 'Lax'
SESSION_COOKIE_NAME          = 'heka_sid'

# ── CSRF ──────────────────────────────────────────────────────────────────────
CSRF_COOKIE_HTTPONLY     = False
CSRF_COOKIE_SAMESITE     = 'Lax'
CSRF_COOKIE_NAME         = 'heka_csrf'
CSRF_TRUSTED_ORIGINS     = ['https://soporte.heka.com.ec']  # ← NUEVO
SECURE_SSL_REDIRECT = False # Déjalo en False ya que Nginx maneja el SSL de forma externa

# ── Proxy SSL — Django entiende que Nginx ya terminó el TLS ──────────────────
SECURE_PROXY_SSL_HEADER  = ('HTTP_X_FORWARDED_PROTO', 'https')  # ← NUEVO

# ── Seguridad de headers ──────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER   = True
X_FRAME_OPTIONS              = 'DENY'

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'heka-cache',
    }
}

# ── REST Framework ────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/minute',
        'user': '100/minute',
    },
}

# ── JWT ───────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':    timedelta(minutes=env.int('JWT_ACCESS_TOKEN_LIFETIME_MINUTES', default=30)),
    'REFRESH_TOKEN_LIFETIME':   timedelta(days=env.int('JWT_REFRESH_TOKEN_LIFETIME_DAYS', default=1)),
    'ROTATE_REFRESH_TOKENS':    True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES':        ('Bearer',),
    'AUTH_TOKEN_CLASSES':       ('rest_framework_simplejwt.tokens.AccessToken',),
    'ALGORITHM':                'HS256',
}

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS   = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

# ── Celery ────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL        = env('CELERY_BROKER_URL',     default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND    = env('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TASK_SERIALIZER   = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE          = 'America/Guayaquil'
CELERY_BEAT_SCHEDULER    = 'django_celery_beat.schedulers:DatabaseScheduler'

# ── Localización ──────────────────────────────────────────────────────────────
LANGUAGE_CODE = 'es'
TIME_ZONE     = 'America/Guayaquil'
USE_I18N      = True
USE_TZ        = False    # ← CORREGIDO: estaba False

# ── Archivos estáticos y media ────────────────────────────────────────────────
STATIC_URL       = '/static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_BACKEND       = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST          = env('EMAIL_HOST',          default='smtp.office365.com')
EMAIL_PORT          = env.int('EMAIL_PORT',      default=587)
EMAIL_HOST_USER     = env('EMAIL_HOST_USER',     default='soporte@heka.com.ec')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS       = env.bool('EMAIL_USE_TLS',  default=True)
EMAIL_USE_SSL       = env.bool('EMAIL_USE_SSL',  default=False)
EMAIL_TIMEOUT       = 10
DEFAULT_FROM_EMAIL  = env('EMAIL_HOST_USER',     default='')
