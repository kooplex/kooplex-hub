# kooplexhub/management/commands/kooplexhuey.py

from django_huey.management.commands.djangohuey import (
    Command as HueyCommand,
)
from django_huey import (
    get_queue, 
    get_queue_name,
)

from hub.huey_diagnostics import report_backlog


class Command(HueyCommand):

    def handle(self, *args, **options):
        queue_name = get_queue_name(options.get("queue") or None)
        queue = get_queue(queue_name)

        report_backlog(queue, queue_name)

        return super().handle(*args, **options)
