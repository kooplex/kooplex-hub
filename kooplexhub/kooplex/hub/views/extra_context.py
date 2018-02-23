from django.contrib import messages

from kooplex.lib import get_settings

def extra_context(request):
    return {
        'year': 2018,
        'messages': messages.get_messages(request),
        'title': 'Kooplex Collaborative Framework',
        'base_url': get_settings('hub', 'base_url'),
    }

