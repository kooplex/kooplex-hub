import uuid

from django.utils.text import slugify


def generate_container_label(*, user, name):
    base = slugify(
        f"{user.username}-{name}"
    ) or "container"

    return (
        f"{base[:180]}-"
        f"{uuid.uuid4().hex[:8]}"
    )

