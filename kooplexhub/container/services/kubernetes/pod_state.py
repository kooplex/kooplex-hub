"""Pure interpretation of Kooplex Pod and Deployment runtime state.

This module deliberately contains no Django or Kubernetes API calls.  It can be
unit-tested with simple objects and is shared by the long-running watcher.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable

from .labels import instance_name_from_object


class RuntimeState(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    NOTPRESENT = "notpresent"
    ERROR = "error"


@dataclass(frozen=True)
class RuntimeObservation:
    state: RuntimeState
    backend_state: str
    node_name: str | None = None
    pod_name: str | None = None
    pod_uid: str | None = None


_STARTING_REASONS = {
    "ContainerCreating",
    "PodInitializing",
    "Scheduled",
    "Pulling",
    "Pulled",
    "Created",
}

_ERROR_REASONS = {
    "ErrImagePull",
    "ImagePullBackOff",
    "CreateContainerConfigError",
    "CrashLoopBackOff",
    "RunContainerError",
    "CreateContainerError",
    "InvalidImageName",
    "Failed",
    "FailedMount",
    "FailedCreatePodSandBox",
    "Evicted",
    "OOMKilled",
    "ContainerCannotRun",
    "DeadlineExceeded",
    "Unschedulable",
}


def select_effective_pod(pods: Iterable[Any]) -> Any | None:
    """Choose the Pod that currently represents the logical workload.

    Deployment rollouts may briefly expose an old terminating Pod together with
    a new Pending Pod.  A non-terminating replacement must win over the old Pod.
    Within the same termination class, prefer Running, then Pending, then the
    newest remaining Pod.
    """

    candidates = list(pods)
    if not candidates:
        return None

    non_terminating = [
        pod
        for pod in candidates
        if getattr(getattr(pod, "metadata", None), "deletion_timestamp", None)
        is None
    ]
    if non_terminating:
        candidates = non_terminating

    phase_priority = {
        "Running": 0,
        "Pending": 1,
        "Unknown": 2,
        "Failed": 3,
        "Succeeded": 4,
    }

    def creation_time(pod: Any) -> float:
        timestamp = getattr(
            getattr(pod, "metadata", None), "creation_timestamp", None
        )
        try:
            return float(timestamp.timestamp())
        except (AttributeError, TypeError, ValueError):
            return 0.0

    candidates.sort(
        key=lambda pod: (
            phase_priority.get(
                getattr(getattr(pod, "status", None), "phase", None), 99
            ),
            -creation_time(pod),
        )
    )
    return candidates[0]


def observe_pod(pod: Any) -> RuntimeObservation:
    metadata = getattr(pod, "metadata", None)
    spec = getattr(pod, "spec", None)
    status = getattr(pod, "status", None)

    pod_name = getattr(metadata, "name", None)
    pod_uid = getattr(metadata, "uid", None)
    node_name = getattr(spec, "node_name", None)
    phase = getattr(status, "phase", None)
    pod_reason = getattr(status, "reason", None)

    def result(state: RuntimeState, backend_state: str) -> RuntimeObservation:
        return RuntimeObservation(
            state=state,
            backend_state=backend_state,
            node_name=node_name,
            pod_name=pod_name,
            pod_uid=str(pod_uid) if pod_uid is not None else None,
        )

    if getattr(metadata, "deletion_timestamp", None) is not None:
        return result(RuntimeState.STOPPING, "Killing")

    if pod_reason in _ERROR_REASONS:
        return result(RuntimeState.ERROR, pod_reason)

    init_observation = _observe_init_containers(status)
    if init_observation is not None:
        return result(*init_observation)

    main_status = _main_container_status(pod)
    if main_status is not None:
        state = getattr(main_status, "state", None)
        waiting = getattr(state, "waiting", None) if state else None
        running = getattr(state, "running", None) if state else None
        terminated = getattr(state, "terminated", None) if state else None

        if waiting is not None:
            reason = getattr(waiting, "reason", None) or "Waiting"
            mapped = (
                RuntimeState.ERROR
                if reason in _ERROR_REASONS
                else RuntimeState.STARTING
            )
            return result(mapped, reason)

        if running is not None:
            return result(RuntimeState.RUNNING, "Running")

        if terminated is not None:
            reason = getattr(terminated, "reason", None)
            exit_code = int(getattr(terminated, "exit_code", 1) or 0)
            if not reason:
                reason = "Completed" if exit_code == 0 else "Failed"
            mapped = (
                RuntimeState.NOTPRESENT
                if exit_code == 0 and reason in {"Completed", "Succeeded"}
                else RuntimeState.ERROR
            )
            return result(mapped, reason)

    scheduled_problem = _pod_scheduling_problem(status)
    if scheduled_problem is not None:
        reason, is_error = scheduled_problem
        return result(
            RuntimeState.ERROR if is_error else RuntimeState.STARTING,
            reason,
        )

    if phase == "Running":
        # Pod phase can become Running a fraction before containerStatuses is
        # populated.  Do not claim the user container is ready yet.
        return result(RuntimeState.STARTING, "ContainerStatusPending")
    if phase == "Pending" or phase is None:
        return result(RuntimeState.STARTING, phase or "Pending")
    if phase == "Failed":
        return result(RuntimeState.ERROR, pod_reason or "Failed")
    if phase == "Succeeded":
        return result(RuntimeState.NOTPRESENT, "Succeeded")
    if phase == "Unknown":
        return result(RuntimeState.ERROR, pod_reason or "Unknown")

    return result(RuntimeState.STARTING, str(phase or "Pending"))


def observe_deployment(deployment: Any | None) -> RuntimeObservation:
    """Describe a workload when no Pod is currently visible."""

    if deployment is None:
        return RuntimeObservation(
            RuntimeState.NOTPRESENT,
            "Not Found",
        )

    metadata = getattr(deployment, "metadata", None)
    spec = getattr(deployment, "spec", None)
    status = getattr(deployment, "status", None)

    if getattr(metadata, "deletion_timestamp", None) is not None:
        return RuntimeObservation(
            RuntimeState.STOPPING,
            "DeploymentDeleting",
        )

    for condition in getattr(status, "conditions", None) or []:
        condition_type = getattr(condition, "type", None)
        condition_status = str(getattr(condition, "status", ""))
        reason = getattr(condition, "reason", None)

        if condition_type == "ReplicaFailure" and condition_status == "True":
            return RuntimeObservation(
                RuntimeState.ERROR,
                reason or "ReplicaFailure",
            )
        if (
            condition_type == "Progressing"
            and condition_status == "False"
        ) or reason == "ProgressDeadlineExceeded":
            return RuntimeObservation(
                RuntimeState.ERROR,
                reason or "ProgressDeadlineExceeded",
            )

    replicas = int(getattr(spec, "replicas", 1) or 0)
    if replicas <= 0:
        return RuntimeObservation(
            RuntimeState.NOTPRESENT,
            "DeploymentScaledDown",
        )

    return RuntimeObservation(
        RuntimeState.STARTING,
        "DeploymentWaitingForPod",
    )


def _observe_init_containers(
    pod_status: Any,
) -> tuple[RuntimeState, str] | None:
    for container_status in (
        getattr(pod_status, "init_container_statuses", None) or []
    ):
        state = getattr(container_status, "state", None)
        waiting = getattr(state, "waiting", None) if state else None
        terminated = getattr(state, "terminated", None) if state else None

        if waiting is not None:
            reason = getattr(waiting, "reason", None) or "PodInitializing"
            return (
                RuntimeState.ERROR
                if reason in _ERROR_REASONS
                else RuntimeState.STARTING,
                reason,
            )

        if terminated is not None:
            exit_code = int(getattr(terminated, "exit_code", 1) or 0)
            if exit_code != 0:
                return (
                    RuntimeState.ERROR,
                    getattr(terminated, "reason", None) or "InitContainerError",
                )
    return None


def _main_container_status(pod: Any) -> Any | None:
    status = getattr(pod, "status", None)
    statuses = list(getattr(status, "container_statuses", None) or [])
    if not statuses:
        return None

    preferred_name = instance_name_from_object(pod)
    if preferred_name:
        for container_status in statuses:
            if getattr(container_status, "name", None) == preferred_name:
                return container_status

    spec = getattr(pod, "spec", None)
    regular_names = [
        getattr(container_spec, "name", None)
        for container_spec in getattr(spec, "containers", None) or []
        if getattr(container_spec, "name", None) != "davfs-sidecar"
    ]
    regular_names = [name for name in regular_names if name]
    if len(regular_names) == 1:
        for container_status in statuses:
            if getattr(container_status, "name", None) == regular_names[0]:
                return container_status

    return None


def _pod_scheduling_problem(pod_status: Any) -> tuple[str, bool] | None:
    for condition in getattr(pod_status, "conditions", None) or []:
        if getattr(condition, "type", None) != "PodScheduled":
            continue
        if str(getattr(condition, "status", "")) != "False":
            continue
        reason = getattr(condition, "reason", None) or "Pending"
        return reason, reason in _ERROR_REASONS
    return None
