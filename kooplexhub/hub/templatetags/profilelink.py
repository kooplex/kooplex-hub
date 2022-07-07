from django import template
from django.utils.html import format_html
from django.urls import reverse

register = template.Library()

from kooplexhub.settings import URL_PROFILE

@register.simple_tag
def profilelink(*args, **kwargs):
    return format_html(f"""<li role="menuitem" tabindex="-1" data-menu-id="navbar_profile" name="navbar_profile" style="padding-left: 48px;" class="ant-menu-item"><span class="ant-menu-title-content"> <a href="{URL_PROFILE}" data-toggle="modal" data-target="#profile">Profile</a></span></li>""")

