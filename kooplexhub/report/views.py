import logging
import base64

from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.contrib.auth.decorators import login_required
from django.views import generic
from django.views.decorators.http import require_http_methods
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Q
from django.utils.html import format_html
from django.urls import reverse
import re

from .models import Report, ReportContainerBinding, ReportType, ReportTag
from container.models import Image, Container
from .forms import FormReport
from project.models import Project, UserProjectBinding

logger = logging.getLogger(__name__)

try:
    from kooplexhub.settings import KOOPLEX
except importerror:
    KOOPLEX = {}

class ReportView(LoginRequiredMixin):
    model = Report
    template_name = 'report_configure.html'
    form_class = FormReport
    #context_object_name = 'reports'
    success_url = '/hub/report/list/' #FIXME: django.urls.reverse or shortcuts.reverse does not work reverse('project:list')

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        initial['user'] = user
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_id = self.kwargs.get('pk')
        context['menu_report'] = True
        context['submenu'] = 'configure' if report_id else 'new'
        context['active'] = self.request.COOKIES.get('configure_report_tab', 'meta') if report_id else 'meta'
        context['empty_title'] = format_html("You have no new non-empty folder in the <b>/v/report_prepare</b> directory")
        context['empty_body'] = format_html(f"""<a href=""><i class="bi bi-journal-bookmark-fill"></i><span class="d-none d-sm-inline">&nbsp;Check the manual for further instructions</span></a>""")
        context['url_post'] = reverse('report:configure', args = (report_id, )) if report_id else reverse('report:new')
        context['report_id'] = report_id
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        report_id = form.cleaned_data.pop('report_id')
        if report_id:
            report = Report.objects.get(id = report_id)
            changed = []
            #FIXME: handle tags
            #FIXME: thumbnail not updated BUT why
            for attribute in [ 'name', 'description', 'scope', 'reporttype', 'image', 'indexfile', 'thumbnail' ]:
                value = form.cleaned_data.get(attribute)
                if value and (getattr(report, attribute) != value):
                    setattr(report, attribute, value)
                    changed.append(attribute)
            if changed:
                report.save()
                messages.info(self.request, f'Report{form.cleaned_data["name"]} is updated')
        else:
            report = Report.objects.create(**form.cleaned_data)
            messages.info(self.request, f'Report {form.cleaned_data["name"]} is created')
            if not report.reporttype.is_static:
                logger.debug("Create an env for the report: %s" % (report.name))
                # Create a container
                user = report.creator
                name = re.sub(r'\W+', '', report.name)
                container, created = Container.objects.get_or_create(
                        user = user, 
                        name = name,
                        #friendly_name = report.name,
                        label = f"{user.username}-{name}",
                        image = report.image
                )
                ReportContainerBinding.objects.create(report=report, container=container)
        return super().form_valid(form)


class NewReportView(ReportView, generic.FormView):
    pass


class ConfigureReportView(ReportView, generic.edit.UpdateView):
    pass


        

class ReportListView(generic.ListView):
    template_name = 'report_list.html'
    context_object_name = 'reports'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['submenu'] = 'list'
        context['menu_report'] = True
        context['extend'] = "report_layout.html" if self.request.user.is_authenticated else "index_unauthorized.html"
        context['common_tags'] : Report.tags.most_common()
        return context

    def get_queryset(self):
        user = self.request.user
        public = Q(scope = Report.SC_PUBLIC)
        if not user.is_authenticated:
            return Report.objects.filter(public)
        collaborator = Q(project__in = Project.get_userprojects(user), scope = Report.SC_COLLABORATION)
        creator = Q(creator = user, scope = Report.SC_PRIVATE)
        internal = Q(scope = Report.SC_INTERNAL)
        return Report.objects.filter(public | collaborator | internal | creator)


def open(request, report_id):
    """open report"""
    user = request.user
    try:
        report = Report.objects.get(id = report_id) #, creator = user)
        link = report.url
        logger.debug(f"User {user} opens report {report.id} at link: {link}")
    except Exception as e:
        logger.error(f"User {user} can not open report id={report_id} url= -- {e}")
    return HttpResponseRedirect(link)

@login_required
def delete(request, report_id):
    """delete report"""
    user = request.user
    report = Report.objects.get(id = report_id, creator = user)
    try:
        rcb = ReportContainerBinding.objects.get(report=report)
        rcb.container.stop()
        rcb.delete()
    except Exception as e:
        logger.error(f"User {user} can not delete report id={report_id} -- {e}")
    try:
        report.delete()
        messages.info(request, f"Report {report.name} is deleted")
    except Exception as e:
        logger.error(f"User {user} can not delete report id={report_id} -- {e}")
    return redirect('report:list')


