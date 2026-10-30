"""
celery_app.py  (NO renombrar a celery.py — conflicto con la libreria)
Arrancar con: celery -A celery_app worker --loglevel=info
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE', 'config.settings.production'))

app = Celery('helpdesk')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# celery_tasks/ no es una app de Django (no está en INSTALLED_APPS), así
# que autodiscover_tasks() nunca la encuentra por sí sola -- sin este
# import explícito el worker arranca sin estas tareas registradas y
# cualquier .delay() que le llegue falla con "unregistered task".
import celery_tasks.tasks  # noqa: E402,F401
