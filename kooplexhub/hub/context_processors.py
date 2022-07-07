from kooplexhub import settings
from .models import Note


def next_page(request):
    return { 'next_page': request.POST.get('next_page') } if request.method == 'POST' else { 'next_page': request.GET.get('next_page', 'indexpage') }


def user(request):
    return { 'user': request.user } if request.user.is_authenticated else {}


def notes(request):
    return { 'notes': Note.objects.filter(expired = False) if request.user.is_authenticated else Note.objects.filter(is_public = True, expired = False)}


def installed_apps(request):
    return {
      'app_report_installed': 'report' in settings.INSTALLED_APPS,       
      'app_project_installed': 'project' in settings.INSTALLED_APPS,       
      'app_education_installed': 'education' in settings.INSTALLED_APPS,       
      'app_volume_installed': 'volume' in settings.INSTALLED_APPS,       
      'app_plugin_installed': 'plugin' in settings.INSTALLED_APPS,       
    }


#def table(request):
#    state_req = []
#    for k in ['page', 'sort']:
#        v = request.GET.get(k)
#        if v:
#            state_req.append("%s=%s" % (k, v))
#    return { 'pager': "&".join(state_req) } if len(state_req) else {}

