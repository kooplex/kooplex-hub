from hub.forms import FormBiography
from hub.forms import FormProject
from hub.forms import FormService
from hub.models import Project

from kooplex.settings import KOOPLEX

def next_page(request):
    return { 'next_page': request.POST.get('next_page') } if request.method == 'POST' else { 'next_page': request.GET.get('next_page', 'indexpage') }

def form_biography(request):
    return { 'f_bio': FormBiography(instance = request.user.profile) } if hasattr(request.user, 'profile') else {}

def form_project(request):
    return { 'f_project_meta': FormProject(user = request.user, auto_id = 'id_newproject_%s') } if request.user.is_authenticated else {}

def form_environment(request):
    return { 'f_environment_meta': FormService(auto_id = 'id_service_%s') } if request.user.is_authenticated else {}

def user(request):
    return { 'user': request.user } if request.user.is_authenticated else {}

def manual(request):
    return { 'url_manual': KOOPLEX['url_manual'] }

def table(request):
    state_req = []
    for k in ['page', 'sort']:
        v = request.GET.get(k)
        if v:
            state_req.append("%s=%s" % (k, v))
    return { 'pager': "&".join(state_req) } if len(state_req) else {}

