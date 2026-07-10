from dataclasses import dataclass

from django.utils import timezone

from ..conf import CONTAINER_SETTINGS
from ..models import Container


@dataclass
class ContainerRuntimePresenter:
    container: Container

    @property
    def state(self):
        return self.container.state

    @property
    def wants_running(self):
        return bool(self.container.require_running)

    @property
    def is_not_present(self):
        return self.state == Container.State.NOTPRESENT

    @property
    def is_starting(self):
        return self.state == Container.State.STARTING

    @property
    def is_running(self):
        return self.state == Container.State.RUNNING

    @property
    def is_stopping(self):
        return self.state == Container.State.STOPPING

    @property
    def is_restarting(self):
        return self.is_stopping and self.wants_running

    @property
    def needs_restart(self):
        return self.state == Container.State.NEED_RESTART

    @property
    def is_error(self):
        return self.state == Container.State.ERROR

    @property
    def is_transitioning(self):
        return self.is_starting or self.is_stopping

    @property
    def can_start(self):
        if self.is_transitioning:
            return False

        return self.state in [
            Container.State.NOTPRESENT,
            Container.State.ERROR,
        ]

    @property
    def can_stop(self):
        if self.is_transitioning and not self.is_starting:
            return False

        return self.state in [
            Container.State.STARTING,
            Container.State.RUNNING,
            Container.State.NEED_RESTART,
            Container.State.ERROR,
        ]

    @property
    def can_restart(self):
        return self.state == Container.State.NEED_RESTART

    @property
    def can_fetchlog(self):
        return self.state in [
            Container.State.STARTING,
            Container.State.RUNNING,
            Container.State.NEED_RESTART,
            Container.State.ERROR,
            Container.State.STOPPING,
        ]

    @property
    def start_button_class(self):
        if self.is_starting:
            return "is-pending"
        if self.can_start:
            return "is-start"
        return "is-neutral"

    @property
    def stop_button_class(self):
        if self.is_stopping and not self.is_restarting:
            return "is-pending"
        if self.can_stop:
            return "is-stop"
        return "is-neutral"

    @property
    def restart_button_class(self):
        if self.is_restarting:
            return "is-pending"
        if self.can_restart:
            return "is-restart"
        return "is-neutral"

    @property
    def start_title(self):
        if self.is_starting:
            return "Environment is starting."
        if self.is_running:
            return "Environment is already running."
        if self.is_stopping:
            return "Environment is stopping."
        if self.needs_restart:
            return "Environment needs restart."
        return "Start environment."

    @property
    def stop_title(self):
        if self.is_restarting:
            return "Environment is restarting."
        if self.is_stopping:
            return "Environment is stopping."
        if self.is_not_present:
            return "Environment is not running."
        return "Stop environment."

    @property
    def restart_title(self):
        if self.is_restarting:
            return "Environment is restarting."
        if self.needs_restart:
            return self.container.restart_reasons or "Restart required."
        return "Restart not required."

    @property
    def phase_class(self):
        if self.is_restarting:
            return "restarting"
        if self.is_starting:
            return "starting"
        if self.is_stopping:
            return "stopping"
        if self.needs_restart:
            return "restart"
        if self.is_running:
            return "running"
        if self.is_error:
            return "error"
        return "stopped"

    @property
    def phase_label(self):
        if self.is_restarting:
            return "Restarting..."
        return self.container.get_state_display()

    @property
    def backend_label(self):
        return self.container.state_backend or "None"

    @property
    def requested_node_label(self):
        return self.container.requested_node or "-"
    
    
    @property
    def runtime_node_label(self):
        return self.container.runtime_node or "-"

    @property
    def uptime_min(self):
        return CONTAINER_SETTINGS.kubernetes.resources.min_idletime
    
    
    @property
    def uptime_max(self):
        return CONTAINER_SETTINGS.kubernetes.resources.max_idletime
    
    
    @property
    def requested_uptime(self):
        return self.container.requested_uptime_hours or self.uptime_min
    
    
    @property
    def uptime_is_editable(self):
        return not self.is_transitioning
    
    
    @property
    def show_uptime_progress(self):
        return self.container.is_running
    
    
    @property
    def idle_elapsed_hours(self):
        """
        Assumes Container.idle is stored in minutes.
    
        Change this conversion if `idle` already stores hours.
        """
        if self.container.idle is None:
            return 0
    
        return max(0, self.container.idle / 60)
    
    
    @property
    def idle_progress_percent(self):
        maximum = self.requested_uptime
    
        if not maximum:
            return 0
    
        percent = self.idle_elapsed_hours / maximum * 100
        return min(100, max(0, round(percent)))
    
    
    @property
    def idle_elapsed_label(self):
        minutes = self.container.idle
    
        if minutes is None:
            return "0 min"
    
        hours, remaining_minutes = divmod(int(minutes), 60)
    
        if hours:
            return f"{hours} h {remaining_minutes} min"
    
        return f"{remaining_minutes} min"
    
    
    @property
    def uptime_limit_label(self):
        return f"{self.requested_uptime} h"
