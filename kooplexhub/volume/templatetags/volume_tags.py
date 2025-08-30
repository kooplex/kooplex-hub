from django import template
register = template.Library()

@register.inclusion_tag("volume/card.html")
def render_volume(volume):
    return {"volume": volume}

@register.inclusion_tag("widgets/volume_scope.html")
def render_scope(volume):
    return {"volume": volume}

