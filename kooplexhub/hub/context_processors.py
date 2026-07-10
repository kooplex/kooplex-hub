from kooplexhub import settings
from .models import Note
from django.urls import reverse
from django.utils.html import format_html
from django.templatetags.static import static

def navigation_context(request):
    if not request.user.is_authenticated:
        return {
            "page_title": "Kooplex - Reports",
            "nav_items": [],
            "active": None,
            "current_nav_label": "Reports",
        }
    NAV_ITEMS = getattr(settings, 'MENU', [])
    active = None
    current_nav_label = None

    view_name = getattr(request.resolver_match, "view_name", "")

    for item in NAV_ITEMS:
        if view_name == item["url_name"] or view_name.startswith(item["url_name"].split(":")[0] + ":"):
            active = item["key"]
            current_nav_label = item["label"]
            break

    return {
        "page_title": "Kooplex - " + item["label"],
        "nav_items": NAV_ITEMS,
        "active": active,
        "current_nav_label": current_nav_label,
    }


def user(request):
    return { 'user': request.user } if request.user.is_authenticated else {}


def notes(request):
    return { 'notes': Note.objects.filter(expired = False) if request.user.is_authenticated else Note.objects.filter(is_public = True, expired = False)}

def url_login(request):
    return { 'url_login': settings.LOGIN_URL }
