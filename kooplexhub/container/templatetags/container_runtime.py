from django import template

from ..services.runtime_presenter import ContainerRuntimePresenter
from ..services.compute_presenter import ContainerComputePresenter

register = template.Library()


@register.simple_tag
def runtime_for(container):
    return ContainerRuntimePresenter(container)


@register.simple_tag
def compute_for(container):
    return ContainerComputePresenter(container)
