from django import template

from container.services.runtime_presenter import ContainerRuntimePresenter

register = template.Library()


@register.simple_tag
def runtime_for(container):
    return ContainerRuntimePresenter(container)
