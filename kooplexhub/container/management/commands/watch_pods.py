import logging

from django.core.management.base import BaseCommand

from container.services.kubernetes.watcher import ManagedPodWatcher
from container.services.kubernetes.wiring import build_clients
from container.services.live import broadcast_container_runtime_changed

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Watch Deployment-managed Kooplex Pods and synchronize Container state"

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch-timeout",
            type=int,
            default=60,
            help="Seconds before relisting Pods and Deployments (default: 60)",
        )
        parser.add_argument(
            "--reconnect-delay",
            type=float,
            default=5.0,
            help="Seconds to wait after a watcher error (default: 5)",
        )

    def handle(self, *args, **options):
        watcher = ManagedPodWatcher(
            build_clients(),
            feedback=self.feedback,
            watch_timeout_seconds=options["watch_timeout"],
            reconnect_delay_seconds=options["reconnect_delay"],
        )
        watcher.run_forever()

    @staticmethod
    def feedback(container, message, backend_state=None):
        broadcast_container_runtime_changed(
            container=container,
            reason=message,
            backend_state=backend_state,
        )
