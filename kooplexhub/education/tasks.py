from django.utils import timezone
from django.db.models import Q
from django_huey import db_task, db_periodic_task
from huey import crontab

from education.models import Assignment


@db_periodic_task(
    crontab(minute="*"), 
    queue="course",
)
def check_handout_and_collect():
    from education.services.assignments import (
        handout_assignment_automatically,
        collect_assignment_automatically,
    )

    now=timezone.now()

    handout_candidates = (
        Assignment.objects
        .filter(
            valid_from__isnull=False,
            valid_from__lte=now,
        )
        .filter(
            Q(expires_at__isnull=True)
            | Q(expires_at__gt=now)
        )
    )

    for assignment in handout_candidates:
        handout_assignment_automatically(
            assignment=assignment
        )

    for assignment in (
        Assignment.objects
        .filter(
            expires_at__isnull=False,
            expires_at__lte=now,
        )
    ):
        collect_assignment_automatically(
            assignment=assignment
        )


@db_task(queue="course")
def assignment_prepare(assignment_id):
    from .services.assignment_filesystem import (
        perform_assignment_snapshot,
    )

    perform_assignment_snapshot(
        assignment_id=assignment_id,
    )


@db_task(queue="course")
def assignment_handout(binding_id):
    from education.services.assignment_filesystem import (
        perform_assignment_handout,
    )

    perform_assignment_handout(
        binding_id=binding_id,
    )


@db_task(queue="course")
def assignment_collect(binding_id):
    from education.services.assignment_filesystem import (
        perform_assignment_collection,
    )

    perform_assignment_collection(
        binding_id=binding_id,
    )

