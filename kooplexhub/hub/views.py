from django.views import generic
from django.contrib.auth.mixins import AccessMixin


class IndexView(AccessMixin, generic.TemplateView):
    template_name = 'index.html'
    context_object_name = 'indexpage'



