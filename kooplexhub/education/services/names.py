from django.core.exceptions import ValidationError

from ..models import Course

MIN_NAME_LENGTH = 3


def validate_course_name(
    *,
    name,
    exclude_course=None,
):
    normalized_name = name.strip()

    if not normalized_name:
        raise ValidationError(
            "Enter a course name."
        )

    if len(normalized_name) < MIN_NAME_LENGTH:
        raise ValidationError(
            f"Name must be at least "
            f"{MIN_NAME_LENGTH} characters."
        )

    courses = Course.objects.filter(
        name__iexact=normalized_name,
    )

    if exclude_course is not None:
        coursess = courses.exclude(
            pk=exclude_course.pk,
        )

    if courses.exists():
        raise ValidationError(
            f"A course already exists with this name."
        )

    return normalized_name


