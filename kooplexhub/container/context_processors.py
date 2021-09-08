
from .forms import FormContainer
from .forms import FormAttachment
from .models import Container

#from hub.forms import FormImage

def form_container(request):
    return { 'f_environment_meta': FormContainer(auto_id = 'id_service_%s') } if request.user.is_authenticated else {}


def warnings(request):
    user = request.user
    return { 
        'unbound_containers': Container.objects.filter(user = user).exclude(projectcontainerbinding__gt = 0).exclude(coursecontainerbinding__gt = 0), #FIXME: .exclude(reportcontainerbinding__gt = 0),
        'restart_containers': Container.objects.filter(user = user, state = Container.ST_NEED_RESTART),
    } if user.is_authenticated else {}


def form_attachment(request):
    return { 'f_newattachment': FormAttachment(auto_id = 'id_newattachment_%s') } if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.can_createattachment else {}


