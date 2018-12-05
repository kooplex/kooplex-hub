from hub.forms import FormBiography

def form_biography(request):
    return { 'f_bio': FormBiography(instance = request.user.profile) } if hasattr(request.user, 'profile') else {}

def user(request):
    return { 'user': request.user } if request.user.is_authenticated else {}

def table(request):
    state_req = []
    for k in ['page', 'sort']:
        v = request.GET.get(k)
        if v:
            state_req.append("%s=%s" % (k, v))
    return { 'pager': "&".join(state_req) } if len(state_req) else {}

