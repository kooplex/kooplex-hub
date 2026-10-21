"""Read a plain-text member list without changing stored memberships."""
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils.html import format_html

MAX_BYTES = 256 * 1024
MAX_LINES = 2000


def import_members(request, *, membership_ui, default_role):
    upload = request.FILES.get("members_file")
    if upload is None:
        return "", "Choose a UTF-8 text file.", True
    if upload.size > MAX_BYTES:
        return "", "File exceeds the 256 KiB limit.", True
    try:
        content = upload.read(MAX_BYTES + 1).decode("utf-8-sig")
    except UnicodeDecodeError:
        return "", "File must contain UTF-8 text.", True
    lines = [(n, line.strip()) for n, line in enumerate(content.splitlines(), 1) if line.strip()]
    if len(lines) > MAX_LINES:
        return "", "File exceeds the 2,000 nonblank line limit.", True

    selected = {int(s) for s in request.POST.getlist("member_users") if s.isdigit()}
    selected.add(request.user.pk)
    values = set(line for _, line in lines)
    User = get_user_model()
    candidates = User.objects.filter(is_active=True).filter(
        Q(username__in=values) | Q(email__in=values)
    )
    lookup = {}
    for user in candidates:
        for key in (user.username, user.email):
            if key in values:
                lookup.setdefault(key, []).append(user)

    rows = []
    unmatched = []
    already = 0
    for lineno, value in lines:
        users = {user.pk: user for user in lookup.get(value, [])}
        if len(users) != 1:
            unmatched.append((lineno, value))
            continue
        user = next(iter(users.values()))
        if user.pk in selected:
            already += 1
            continue
        selected.add(user.pk)
        rows.append(render_to_string("ui/editors/membership/row.html", {
            "member": {"user": user, "role": default_role},
            "membership_ui": membership_ui,
        }, request=request))
    message = (
        f"Read {len(lines)} nonblank lines: {len(rows)} added, "
        f"{already} already selected, {len(unmatched)} unmatched or ambiguous."
    )
    if unmatched:
        details = ", ".join(f"{n}: {value}" for n, value in unmatched[:12])
        message += f" Unmatched lines (first 12): {details}"
    return "".join(rows), message, False


def render_import_response(request, *, membership_ui, default_role):
    from django.http import HttpResponse
    from django.utils.html import format_html
    rows, message, error = import_members(
        request, membership_ui=membership_ui, default_role=default_role
    )
    status_class = "text-danger" if error else "text-muted"
    status = format_html(
        '<div id="{}-import-status" hx-swap-oob="outerHTML" '
        'class="small mt-1 {}" role="status">{}</div>',
        membership_ui["dom_id"], status_class, message,
    )
    return HttpResponse(str(status) + rows)
