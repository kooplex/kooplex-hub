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

from .models import Report, ReportContainerBinding, ReportType, ReportTag
from container.models import Image, Container
from .forms import FormReport, FormReportConfigure
from project.models import Project, UserProjectBinding

logger = logging.getLogger(__name__)

try:
    from kooplexhub.settings import KOOPLEX
except importerror:
    KOOPLEX = {}

class NewReportView(LoginRequiredMixin, generic.FormView):
    template_name = 'report_new.html'
    form_class = FormReport
    context_object_name = 'reports'
    success_url = '/hub/report/list/' #FIXME: django.urls.reverse or shortcuts.reverse does not work reverse('project:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['menu_report'] = True
        context['submenu'] = 'new'
        context['empty_title'] = "You have no new non-empty folder in the <b>/v/report_prepare</b> directory"
        context['empty_body'] = format_html(f"""<a href=""><i class="bi bi-journal-bookmark-fill"></i><span class="d-none d-sm-inline">&nbsp;Check the manual for further instructions</span></a>""")
        user = request.user
        #profile = user.profile
        #logger.debug("user %s, method: %s" % (user, request.method))
        #context_dict = {
        #}
        #projects = [ upb.project for upb in UserProjectBinding.objects.filter(user = user) ]
        projects = Project.objects.all() 
        #if len(projects) == 0:
        #    messages.warning(request, f'You do not have a project yet')
        #    return redirect('index')

        okay = lambda f: f.okay
        context.update({
            'f_project': list(filter(okay, [ FormReport(user = user, project = p, auto_id = f'id_newreport_%s') for p in projects ])),
        })
        return context

    def form_valid(self, form):
        logger.info(form.cleaned_data)
        user = self.request.user
        friendly_name = form.cleaned_data['friendly_name']
        Container.objects.create(
            user = user, 
            name = form.cleaned_data['name'], 
            friendly_name = friendly_name, 
            image = form.cleaned_data['image']
        )
        messages.info(self.request, f'Report {friendly_name} is created')
        return super().form_valid(form)

## TODO add suitable permission for folders and files according to their scopes
@login_required
def new(request):
    """
    """
    user = request.user
    profile = user.profile
    logger.debug("user %s, method: %s" % (user, request.method))
    context_dict = {
    }
    projects = [ upb.project for upb in UserProjectBinding.objects.filter(user = user) ]
    if len(projects) == 0:
        messages.warning(request, f'You do not have a project yet')
        return redirect('index')

    okay = lambda f: f.okay
    context_dict.update({
        'f_project': list(filter(okay, [ FormReport(user = user, project = p, auto_id = f'id_newreport_%s') for p in projects ])),
    })
    context_dict['empty_title'] = "You have no new non-empty folder in the /v/report_prepare/ directory"
    context_dict['empty_body'] = format_html(f"""<a href=""><i class="bi bi-journal-bookmark-fill"></i><span class="d-none d-sm-inline">&nbsp;Check the manual for further instructions</span></a>""")
    return render(request, 'report_new.html', context = context_dict)

@require_http_methods(['POST'])
@login_required
def create(request):
    import re
    """Renders new report form."""
    user = request.user
    logger.debug("user %s, method: %s" % (user, request.method))
    try:
        kw = dict()
        password = request.POST.get('password')
        if password:
            kw.update( { 'password': password } )
        try:
            thumbnail = b''.join([ c for c in request.FILES['file'].chunks() ])
        except:
            raise
        report = Report.objects.create(
            name = request.POST.get('name'),
            creator = user,
            project =  Project.objects.get(id = request.POST.get('project_selected')),
            description = request.POST.get('description'),
            scope = request.POST.get('scope'),
            reporttype = ReportType.objects.get(id = request.POST.get('reporttype')),
            indexfile = request.POST.get('indexfile'),
            folder = request.POST.get('folder'),
            thumbnail = thumbnail,
#            folder = request.POST.get('folder'),
            **kw
        )
        if not report.reporttype.is_static:
            logger.debug("Create an env for the report: %s" % (report.name))
            image = Image.objects.get(id = request.POST.get('image'))
            kw.update( { 'image': image } )
            report.image = image
            report.save()

            # Create a container
            container, created = Container.objects.get_or_create(
                    user = user, 
                    name = re.sub(r'\W+', '', request.POST.get('name')),
                    friendly_name = request.POST.get('name'),
                    image = image
            )
            ReportContainerBinding.objects.create(report=report, container=container)
        
        messages.info(request, f"Report {report.name} is created")
        return redirect('report:list')
    except Exception as e:
        logger.error(e)
        raise


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


@login_required
def configure(request, report_id):
    """configure report"""
    user = request.user
    try:
        r = Report.objects.get(id = report_id, creator = user)
        f = FormReportConfigure(instance = r)
        return render(request, 'configure.html', context = { 'form': f, 'report_id': r.id, 'thumbnail': base64.b64encode(r.thumbnail).decode() })
    except Exception as e:
        raise
    return redirect('report:list')


@login_required
def modify(request):
    """delete report"""
    user = request.user
    try:
        r = Report.objects.get(id = request.POST.get('report_id'), creator = user)
        f = FormReportConfigure(request.POST, instance = r)
        if f.is_valid():
            rmod = f.save(commit = False)
            thumbnail_file = request.FILES.get('file', None)
            if thumbnail_file:
                thumbnail = b''.join([ c for c in thumbnail_file.chunks() ]) #FIXME: do some conversion so that we don't need to worry about resolution and representation
                rmod.thumbnail = thumbnail
            rmod.save()
    except Exception as e:
        raise
    return redirect('report:list')

