from django_huey import db_task


@db_task(
    queue='container', 
    retries=3, 
    retry_delay=10,
)
def start_container(user_id, container_id):
    from ..models import Container
    from ..services.kubernetes.wiring import build_runtime_service

    container = Container.objects.select_related("user", "image").get(
        user_id=user_id,
        pk=container_id,
    )
    return build_runtime_service().start(container, remove_legacy_pod=True)


@db_task(
    queue='container', 
    retries=3, 
    retry_delay=10,
)
def stop_container(user_id, container_id):
    from ..models import Container
    from ..services.kubernetes.wiring import build_runtime_service

    container = Container.objects.select_related("user", "image").get(
        user_id=user_id,
        pk=container_id,
    )
    return build_runtime_service().stop(container)


@db_task(
    queue='container', 
    retries=3, 
    retry_delay=10,
)
def restart_container(user_id, container_id):
    from ..models import Container
    from ..services.kubernetes.wiring import build_runtime_service

    container = Container.objects.select_related("user", "image").get(
        user_id=user_id,
        pk=container_id,
    )
    return build_runtime_service().restart(container)
