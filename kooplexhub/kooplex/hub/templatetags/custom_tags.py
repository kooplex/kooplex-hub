from django.template import Variable, VariableDoesNotExist
from django import template

register = template.Library()

@register.assignment_tag()
def resolve(lookup, target):
    try:
        for V in lookup:
            if V.project_id == target:
                return V

    except VariableDoesNotExist:
        return None

@register.filter()
def return_item(l, i):
    try:
        return l[i]
    except:
        return None
