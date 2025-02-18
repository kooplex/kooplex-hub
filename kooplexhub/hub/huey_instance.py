from django.db import close_old_connections, transaction
import huey.api

# Get reference to the original _emit() function
original_emit = huey.api.Huey._emit

def patched_emit(self, signal, task, *args, **kwargs):
    """Ensure fresh DB connection before logging Huey task signals."""
    close_old_connections()  # Prevent stale DB connections before signal logging

    with transaction.atomic():
        return original_emit(self, signal, task, *args, **kwargs)

# Patch Huey’s signal emission function
huey.api.Huey._emit = patched_emit

