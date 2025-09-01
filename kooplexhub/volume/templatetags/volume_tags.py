from django import template
register = template.Library()

@register.inclusion_tag("volume/card.html")
def render_volume(volume):
    return {"volume": volume}

@register.inclusion_tag("volume/scope.html")
def render_scope(volume):
    return {"volume": volume}

@register.simple_tag
def render_usercontainers(volume, user):
    return ", ".join(volume.usercontainer_names(user))
