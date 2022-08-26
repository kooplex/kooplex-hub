import os

from celery import Celery


#os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_celery.settings")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kooplexhub.settings")

#app = Celery("django_celery")
app = Celery("kooplexhub")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
