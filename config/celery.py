"""Celery application: `celery -A config worker` / `celery -A config beat`.

Settings are the `CELERY_*` ones of `config/settings.py` (the periodic tasks are `CELERY_BEAT_SCHEDULE`
there), tasks live in the `tasks.py` of each app.
"""
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("dommaster")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
