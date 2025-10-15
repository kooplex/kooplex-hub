from kooplexhub import settings
from .models import Note
from django.urls import reverse
from django.utils.html import format_html
from django.templatetags.static import static
import re

__r_ref = re.compile(r'^(\w+):\w+$')
__r_static = re.compile(r'^static:(.+)$')
__r_ext = re.compile(r'^https?://[\w-]+\.[\w-]+')
__r_ico = re.compile(r'^\w+\s+[\w-]*$')

def menu(request):
    #TODO: const -> memcache?
    url = request.get_full_path()
    menu = []
    for item in getattr(settings, 'MENU', []):
        icon = item.get('icon')
        target = item.get('target')
        if re.match(__r_ext, icon):
            item['ico'] = format_html(f'<img src="{icon}" alt="[]" class="pe-1">')
        elif re.match(__r_ico, icon):
            item['ico'] = format_html(f'<i class="{icon} pe-1"></i>')
        elif re.match(__r_static, icon):
            ptr = re.split(__r_static, icon)[1]
            src=static(ptr)
            item['ico'] = format_html(f'<img src="{src}" alt="[]" pe-1">')
        else:
            item['ico'] = ''
        if re.match(__r_ext, target):
            item['tgt']=target
            menu.append(item)
        elif re.match(__r_ref, target):
            app = re.split(__r_ref, target)[1]
            if app in settings.INSTALLED_APPS:
                tgt=reverse(item['target'])
                item['active']= 'active border-1 border-start' if tgt == url else ''
                item['tgt']=tgt
                menu.append(item)
        #TODO: add separator filter here
    #raise Exception(str( menu ))
    return { 'menu': menu }


def user(request):
    return { 'user': request.user } if request.user.is_authenticated else {}


def notes(request):
    return { 'notes': Note.objects.filter(expired = False) if request.user.is_authenticated else Note.objects.filter(is_public = True, expired = False)}

def url_login(request):
    return { 'url_login': settings.LOGIN_URL }
