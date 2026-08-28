from .kubernetes.wiring import (
    build_pod_operations,
)


def get_container_log(container):
    return (
        build_pod_operations()
        .logs_for_container(container)
    )


