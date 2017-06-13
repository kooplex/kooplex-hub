from django.conf import settings

def extra_context(request):
    return {'base_url': settings.KOOPLEX_BASE_URL}


