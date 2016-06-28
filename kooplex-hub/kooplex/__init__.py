"""
Package for kooplex.
"""

import os
import django
from django.apps import apps


if 'VISUALSTUDIOVERSION' in os.environ and 'SERVER_PORT' not in os.environ and django.VERSION[:2] >= (1, 7) and not apps.ready:
    # Django 1.7 requires an explicit setup() when running tests in PTVS
    def setUpClass(cls):
        super(ViewTest, cls).setUpClass()
        django.setup()