from .models import UserProjectBinding, ProjectContainerBinding
from django.db.models import Exists, OuterRef

def warnings(request):
    user = request.user
    return { 
        'unbound_projects': UserProjectBinding.objects.filter(user=user).annotate(
                                has_container=Exists(
                                    ProjectContainerBinding.objects.filter(
                                        project=OuterRef('project'),
                                        container__user=OuterRef('user')
                                    )
                                )
                            ).filter(has_container=False),
    } if user.is_authenticated else {}
