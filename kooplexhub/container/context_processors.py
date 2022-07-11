
from .models import Container


def warnings(request):
    user = request.user
    return { 
        'unbound_containers': Container.objects.filter(user = user).exclude(projectcontainerbinding__gt = 0).exclude(coursecontainerbinding__gt = 0), #FIXME: .exclude(reportcontainerbinding__gt = 0),
        'restart_containers': Container.objects.filter(user = user, state = Container.ST_NEED_RESTART),
    } if user.is_authenticated else {}


