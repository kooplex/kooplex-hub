from django import template
from django.utils.html import format_html
from django.urls import reverse
from django.template.defaultfilters import truncatechars

register = template.Library()

instance_id = lambda instance: getattr(instance, 'id', '')

#FIXME deprecate
@register.simple_tag
def field_name(instance=None, instance_type='', cls='p-3'):
    orig = getattr(instance, 'name',  'Add a name')
    return format_html(f"""
<div data-type="text" data-title="Edit {instance_type} name" data-id="{instance_id(instance)}" data-field="name" data-orig="{orig}" data-instance="{instance_type}"
   class="editable fw-bold badge rounded-pill text-dark border border-2 border-dark text-start flex-grow-1 {cls}" data-placement="right">{truncatechars(orig, 45)}</div>
    """)


@register.simple_tag
def field_description(instance = None, instance_type=''):
    orig = getattr(instance, 'description', 'Add a description')
    return format_html(f"""
<div role="button">
    <p class="card-text editable"
       data-type="textarea" data-id="{instance_id(instance)}" data-title="Edit {instance_type} description" data-instance="{instance_type}"
       data-name="description" data-placement="right" data-field="description" data-orig="{orig}"
    >{orig}</p>
</div>
    """)


