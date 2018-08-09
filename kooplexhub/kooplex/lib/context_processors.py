from hub.forms import FormBiography

def form_biography(request):
    return { 'f_bio': FormBiography(instance = request.user.profile) } if hasattr(request.user, 'profile') else {}

def user(request):
    return { 'user': request.user } if request.user.is_authenticated else {}
