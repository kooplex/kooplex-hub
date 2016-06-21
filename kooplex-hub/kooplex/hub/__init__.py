import os
import django
from django.apps import apps

if 'VISUALSTUDIOVERSION' in os.environ and not apps.ready:
    django.setup()
