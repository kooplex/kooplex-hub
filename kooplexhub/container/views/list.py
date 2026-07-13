import logging

from django.views.generic import (
    ListView,
    DetailView,
)
from django.contrib.auth.mixins import LoginRequiredMixin

from ..conf import CONTAINER_SETTINGS
from ..models import Container


logger = logging.getLogger(__name__)


class ContainerListView(
    LoginRequiredMixin, 
    ListView,
):
    template_name = 'container/list.html'
    context_object_name = 'containers'
    model = Container

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Environments",
            "page_eyebrow": "Workspace management",
            "page_description": "Create and manage your notebook environments.",
            "documentation_url": "https://xwiki.vo.elte.hu/en/kooplex-manual/environmentpanel",
            "live_config": {
                "endpoint": CONTAINER_SETTINGS.wss.live.format(user=self.request.user),
            },
            "container_page_config": {
                "userid": self.request.user.id,
                "wss": {
                    "monitor_node": CONTAINER_SETTINGS.wss.monitor_node.format(user=self.request.user),
                },
                "configure_request": "configure-container",
                "model": "container",
                "required": ["name", "image"],
            }
        })
        return context

    def get_queryset(self):
        return Container.objects.filter(user = self.request.user)


class ContainerGridView(
    LoginRequiredMixin, 
    ListView,
):
    template_name = "container/partials/grid.html"
    context_object_name = "containers"
    model = Container

    def get_queryset(self):
        return Container.objects.filter(user=self.request.user)


class ContainerCardPartialView(
    LoginRequiredMixin, 
    DetailView,
):
    model = Container
    template_name = "container/partials/card_wrapper.html"
    context_object_name = "container"

    def get_queryset(self):
        return (
            Container.objects
            .filter(user=self.request.user)
            .select_related("image")
        )


