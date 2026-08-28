from container.models import (
    Proxy,
    ServiceView,
)


def get_container_proxies(container):
    return (
        Proxy.objects
        .filter(
            imagebindings__image_id=(
                container.image_id
            )
        )
        .distinct()
    )


def get_container_service_views(
    container,
    *,
    openable_only=True,
):
    queryset = (
        ServiceView.objects
        .filter(
            proxy__imagebindings__image_id=(
                container.image_id
            )
        )
        .select_related(
            "proxy",
            "icon",
        )
        .distinct()
    )

    if openable_only:
        queryset = queryset.filter(
            openable=True
        )

    return queryset


def get_container_service_view(
    container,
    service_view_id,
):
    return (
        get_container_service_views(
            container
        )
        .filter(pk=service_view_id)
        .first()
    )



