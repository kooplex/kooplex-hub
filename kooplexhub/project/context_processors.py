from .forms import FormProject
from .models import UserProjectBinding


def form_project(request):
    return { 'f_project_meta': FormProject(user = request.user, auto_id = 'id_newproject_%s') } if request.user.is_authenticated and hasattr(request.user, 'profile') and request.user.profile.can_createproject else {}


def warnings(request):
    user = request.user
    return { 
        'unbound_projects': [ upb.project for upb in UserProjectBinding.objects.filter(user = user).exclude(project__projectcontainerbinding__container__user = user) ],
    } if user.is_authenticated else {}
