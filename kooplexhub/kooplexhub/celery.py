import os
from celery import Celery
from celery.signals import setup_logging

@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig
    from django.conf import settings
    dictConfig(settings.LOGGING)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kooplexhub.settings")

app = Celery("kooplexhub")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
