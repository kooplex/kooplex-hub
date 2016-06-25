import os
import django
from django.apps import apps

# Django 1.7 requires an explicit setup() when running tests in PTVS
if 'VISUALSTUDIOVERSION' in os.environ and not apps.ready:
    django.setup()
