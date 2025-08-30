
from .models import Container


def warnings(request):
    user = request.user
    return { 
        'unbound_containers': Container.objects.filter(user = user).exclude(projectbindings__gt = 0).exclude(coursebindings__gt = 0), #FIXME: .exclude(reportcontainerbinding__gt = 0),
        'restart_containers': Container.objects.filter(user = user, state = Container.State.NEED_RESTART),
    } if user.is_authenticated else {}


