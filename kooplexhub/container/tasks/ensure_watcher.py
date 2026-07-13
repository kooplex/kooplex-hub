import logging
import subprocess

from huey import crontab
from django_huey import periodic_task

logger = logging.getLogger(__name__)


@periodic_task(
    crontab(minute="*/5"), 
    queue='container',
)
def ensure_k8s_watcher_running():
    try:
        # Check if the watcher is running
        output = subprocess.check_output(["pgrep", "-f", "manage.py watch_pods"])
        logger.debug(f"Kubernetes watcher is running: {output.decode().strip()}")
    except subprocess.CalledProcessError:
        # Watcher is not running, so restart it
        logger.warning("Kubernetes watcher is not running. Restarting it...")
        subprocess.Popen(
            ["python3", "manage.py", "watch_pods"], 
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
