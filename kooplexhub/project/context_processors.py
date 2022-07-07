from .models import UserProjectBinding


def warnings(request):
    user = request.user
    return { 
        'unbound_projects': [ upb.project for upb in UserProjectBinding.objects.filter(user = user).exclude(project__projectcontainerbinding__container__user = user) ],
    } if user.is_authenticated else {}
