from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from kubernetes.client.exceptions import ApiException
from kubernetes.stream import stream

if TYPE_CHECKING:
    from .client import KubernetesClients
from .labels import selector, workload_labels, workload_name
from .pod_state import select_effective_pod


_NO_LOGS = "There are no environment log messages yet to retrieve"


@dataclass(frozen=True)
class PodLogResult:
    text: str
    pod_name: str | None
    container_name: str | None
    phase: str | None
    available: bool


class PodOperations:
    def __init__(self, clients: "KubernetesClients"):
        self.clients = clients

    def current_pod(self, pod_labels: dict[str, str]) -> Any | None:
        result = self.clients.core.list_namespaced_pod(
            namespace=self.clients.namespace,
            label_selector=selector(pod_labels),
        )
        return select_effective_pod(getattr(result, "items", None) or [])

    def logs_for_container(
        self,
        container: Any,
        *,
        tail_lines: int = 500,
        tail_chars: int | None = 10_000,
        include_previous: bool = True,
    ) -> str:
        result = self.log_result(
            workload_labels(container),
            preferred_container_name=workload_name(container),
            tail_lines=tail_lines,
            include_previous=include_previous,
        )
        text = result.text
        return text[-tail_chars:] if tail_chars is not None else text

    def logs(
        self,
        pod_labels: dict[str, str],
        *,
        container_name: str,
        tail_lines: int = 300,
    ) -> str:
        """Backward-compatible log helper used by the migration facade."""
        return self.log_result(
            pod_labels,
            preferred_container_name=container_name,
            tail_lines=tail_lines,
        ).text

    def log_result(
        self,
        pod_labels: dict[str, str],
        *,
        preferred_container_name: str | None = None,
        tail_lines: int = 500,
        include_previous: bool = True,
    ) -> PodLogResult:
        pod = self.current_pod(pod_labels)
        if pod is None:
            return PodLogResult(_NO_LOGS, None, None, None, False)

        pod_name = pod.metadata.name
        phase = getattr(pod.status, "phase", None)
        container_name = self._resolve_container_name(pod, preferred_container_name)
        if container_name is None:
            names = [c.name for c in getattr(pod.spec, "containers", [])]
            return PodLogResult(
                f"Pod {pod_name} has no readable regular container; containers={names}",
                pod_name,
                None,
                phase,
                False,
            )

        try:
            text = self.clients.core.read_namespaced_pod_log(
                name=pod_name,
                namespace=self.clients.namespace,
                container=container_name,
                tail_lines=tail_lines,
                timestamps=True,
            )
            if text:
                return PodLogResult(text, pod_name, container_name, phase, True)
        except ApiException as exc:
            current_error = exc
        else:
            current_error = None

        # A restarted/crashed container can have useful logs only in the
        # previous instance. This is harmless when no previous instance exists.
        if include_previous and self._restart_count(pod, container_name) > 0:
            try:
                previous = self.clients.core.read_namespaced_pod_log(
                    name=pod_name,
                    namespace=self.clients.namespace,
                    container=container_name,
                    tail_lines=tail_lines,
                    timestamps=True,
                    previous=True,
                )
                if previous:
                    return PodLogResult(
                        previous, pod_name, container_name, phase, True
                    )
            except ApiException:
                pass

        diagnostic = self._container_diagnostic(pod, container_name)
        if current_error is not None:
            diagnostic = (
                f"Could not read logs for {pod_name}/{container_name} "
                f"(HTTP {current_error.status or 'unknown'}): "
                f"{current_error.reason or current_error}. {diagnostic}"
            )
        return PodLogResult(
            diagnostic or _NO_LOGS,
            pod_name,
            container_name,
            phase,
            False,
        )

    def exec_for_container(self, container: Any, command: str) -> str:
        return self.exec_as_user(
            workload_labels(container),
            container_name=workload_name(container),
            username=container.user.username,
            command=command,
        )

    def exec_as_user(
        self,
        pod_labels: dict[str, str],
        *,
        container_name: str,
        username: str,
        command: str,
    ) -> str:
        pod = self.current_pod(pod_labels)
        if pod is None:
            raise RuntimeError("Kooplex pod is not present")
        resolved_name = self._resolve_container_name(pod, container_name)
        if resolved_name is None:
            raise RuntimeError(
                f"Main container {container_name!r} is not present in pod {pod.metadata.name}"
            )
        argv = ["su", "-s", "/bin/bash", username, "-c", command]
        return stream(
            self.clients.core.connect_get_namespaced_pod_exec,
            pod.metadata.name,
            self.clients.namespace,
            command=argv,
            container=resolved_name,
            stderr=True,
            stdin=False,
            stdout=True,
            tty=False,
        )

    @staticmethod
    def _resolve_container_name(
        pod: Any, preferred_container_name: str | None
    ) -> str | None:
        names = [c.name for c in getattr(pod.spec, "containers", [])]
        if preferred_container_name in names:
            return preferred_container_name
        # The known DAVFS sidecar should never be selected as the user log/exec
        # target. This fallback also makes logs survive a historical main-name
        # mismatch during development migration.
        non_sidecars = [name for name in names if name != "davfs-sidecar"]
        if len(non_sidecars) == 1:
            return non_sidecars[0]
        return None

    @staticmethod
    def _status_for(pod: Any, container_name: str) -> Any | None:
        statuses = getattr(pod.status, "container_statuses", None) or []
        for status in statuses:
            if status.name == container_name:
                return status
        return None

    @classmethod
    def _restart_count(cls, pod: Any, container_name: str) -> int:
        status = cls._status_for(pod, container_name)
        return int(getattr(status, "restart_count", 0) or 0)

    @classmethod
    def _container_diagnostic(cls, pod: Any, container_name: str) -> str:
        status = cls._status_for(pod, container_name)
        if status is None:
            return (
                f"Pod {pod.metadata.name} is in phase "
                f"{getattr(pod.status, 'phase', None)!r}; container status is not available yet."
            )

        state = getattr(status, "state", None)
        waiting = getattr(state, "waiting", None) if state else None
        terminated = getattr(state, "terminated", None) if state else None
        running = getattr(state, "running", None) if state else None

        if waiting is not None:
            reason = getattr(waiting, "reason", None) or "Waiting"
            message = getattr(waiting, "message", None)
            return f"Container is waiting: {reason}" + (f" — {message}" if message else "")
        if terminated is not None:
            reason = getattr(terminated, "reason", None) or "Terminated"
            exit_code = getattr(terminated, "exit_code", None)
            message = getattr(terminated, "message", None)
            text = f"Container terminated: {reason}, exit code {exit_code}"
            return text + (f" — {message}" if message else "")
        if running is not None:
            return "Container is running but has not emitted log output yet."
        return _NO_LOGS
