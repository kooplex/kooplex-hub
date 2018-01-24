from django.contrib import messages

def extra_context(request):
    return {
        'year': 2018,
        'messages': messages.get_messages(request),
    }

