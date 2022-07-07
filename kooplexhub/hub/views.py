from django.views import generic
from django.contrib.auth.mixins import AccessMixin


class IndexView(AccessMixin, generic.TemplateView):
    template_name = 'index_unauthorized.html'
    context_object_name = 'indexpage'

    def setup(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            self.template_name = 'index.html'
        super().setup(request, *args, **kwargs)


