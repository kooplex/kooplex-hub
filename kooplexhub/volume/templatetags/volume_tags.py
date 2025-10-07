from django import template
from django.template.loader import render_to_string

register = template.Library()

@register.inclusion_tag("volume/card.html", takes_context=True)
def render_volume(context, volume):
    return {"volume": volume, "user": context.get("request").user }

@register.simple_tag
def render_scope(volume, user, **kwargs):
    is_cell=kwargs.get('td')
    return render_to_string("volume/scope.html", {"volume": volume, "editable": False if is_cell else volume.is_admin(user)})

@register.simple_tag
def render_usercontainers(volume, user):
    return ", ".join(volume.usercontainer_names(user))

@register.simple_tag
def render_description(volume=None, user=None, **kwargs):
    return render_to_string("hub/widgets/inline_textarea.html", {'pk': volume.pk, 'value': volume.description, 'model': 'volume', "editable": volume.is_admin(user),
        'error': kwargs.get('error', None), 'original_value': kwargs.get('original_value')
    })


