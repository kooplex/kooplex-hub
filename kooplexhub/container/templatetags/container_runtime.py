from django import template

from ..services.runtime_presenter import ContainerRuntimePresenter
from ..services.compute_presenter import ContainerComputePresenter
from ..services.mounts import get_container_mount_summary

register = template.Library()


@register.simple_tag
def runtime_for(container):
    return ContainerRuntimePresenter(container)


@register.simple_tag
def compute_for(container):
    return ContainerComputePresenter(container)


@register.simple_tag
def mount_summary_for(container):
    return get_container_mount_summary(container)


