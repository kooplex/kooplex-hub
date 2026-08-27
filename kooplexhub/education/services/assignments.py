import os
import logging
from dataclasses import dataclass

from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import (
    Course,
    UserCourseBinding,
    Assignment,
    UserAssignmentBinding,
)
from ..filesystem import (
    assignment_snapshot_archive,
    course_assignment_prepare_root,
    get_assignment_prepare_subfolders,
)

logger = logging.getLogger(__name__)

MAX_OPERATION_ERROR_LENGTH = 4000

class AssignmentActionError(Exception):
    pass


def clear_operation_error(binding):
    binding.last_operation_error = ""
    binding.last_operation_failed_at = None


def _format_operation_error(error):
    text = (
        f"{error.__class__.__name__}: {error}"
    )

    return text[:MAX_OPERATION_ERROR_LENGTH]


def mark_assignment_preparation_complete(
    *,
    assignment_id,
):
    return (
        Assignment.objects
        .filter(
            pk=assignment_id,
            state=Assignment.State.PREPARING,
        )
        .update(
            state=Assignment.State.READY,
            last_operation_error="",
            last_operation_failed_at=None,
        )
        == 1
    )


def mark_assignment_preparation_failed(
    *,
    assignment_id,
    error,
):
    return (
        Assignment.objects
        .filter(
            pk=assignment_id,
            state=Assignment.State.PREPARING,
        )
        .update(
            state=(
                Assignment.State.PREPARATION_FAILED
            ),
            last_operation_error=(
                _format_operation_error(error)
            ),
            last_operation_failed_at=timezone.now(),
        )
        == 1
    )

def validate_assignment_source(
    *,
    course,
    folder,
):
    root = course_assignment_prepare_root(
        course
    )

    if not os.path.isdir(root):
        raise AssignmentActionError(
            "Course assignment preparation "
            f"directory does not exist: {root}"
        )

    source = os.path.join(
        root,
        folder,
    )

    if not os.path.isdir(source):
        raise AssignmentActionError(
            f'Assignment source folder "{folder}" '
            "does not exist."
        )

    if not os.listdir(source):
        raise AssignmentActionError(
            f'Assignment source folder "{folder}" '
            "is empty."
        )

    if Assignment.objects.filter(
        course=course,
        folder=folder,
    ).exists():
        raise AssignmentActionError(
            f'Assignment source folder "{folder}" '
            "is already used by another assignment."
        )

    return source


@transaction.atomic
def create_assignment(
    *,
    course,
    actor,
    folder,
    name,
    description="",
    valid_from=None,
    expires_at=None,
    remove_collected=False,
    max_size=None,
):
    course = (
        Course.objects
        .filter(
            pk=course.pk,
            userbindings__user=actor,
            userbindings__is_teacher=True,
        )
        .distinct()
        .get()
    )

    folder = str(folder).strip()
    name = str(name).strip()
    description = str(description).strip()

    validate_assignment_source(
        course=course,
        folder=folder,
    )

    #
    # Construct the object first because the archive
    # naming helper can use assignment/course/folder.
    #
    assignment = Assignment(
        course=course,
        creator=actor,
        folder=folder,
        name=name,
        description=description,
        valid_from=valid_from,
        expires_at=expires_at,
        remove_collected=remove_collected,
        max_size=max_size,
        state=Assignment.State.PREPARING,
    )

    assignment.filename = (
        assignment_snapshot_archive(
            assignment
        )
    )

    try:
        assignment.full_clean()
    except ValidationError as error:
        raise AssignmentActionError(
            str(error)
        ) from error

    assignment.save()

    assignment_id = assignment.pk

    def enqueue():
        from ..tasks import assignment_prepare

        logger.debug(
            "Enqueueing assignment snapshot "
            "assignment=%s",
            assignment_id,
        )

        assignment_prepare(
            assignment_id
        )

    transaction.on_commit(enqueue)

    return assignment




def mark_assignment_operation_failed(
    *,
    binding_id,
    expected_state,
    failed_state,
    error,
):
    updated = (
        UserAssignmentBinding.objects
        .filter(
            pk=binding_id,
            state=expected_state,
        )
        .update(
            state=failed_state,
            last_operation_error=(
                _format_operation_error(error)
            ),
            last_operation_failed_at=timezone.now(),
        )
    )

    if updated != 1:
        logger.warning(
            "Could not mark assignment binding %s "
            "as failed: expected state %s",
            binding_id,
            expected_state,
        )

    return updated == 1


def mark_assignment_operation_complete(
    *,
    binding_id,
    expected_state,
    completed_state,
):
    updated = (
        UserAssignmentBinding.objects
        .filter(
            pk=binding_id,
            state=expected_state,
        )
        .update(
            state=completed_state,
            last_operation_error="",
            last_operation_failed_at=None,
        )
    )

    if updated != 1:
        logger.warning(
            "Could not complete assignment binding %s: "
            "expected state %s",
            binding_id,
            expected_state,
        )

    return updated == 1


def mark_assignment_handout_complete(
    *,
    binding_id,
):
    return mark_assignment_operation_complete(
        binding_id=binding_id,
        expected_state=(
            UserAssignmentBinding.State.EXTRACTING
        ),
        completed_state=(
            UserAssignmentBinding.State.WORKINPROGRESS
        ),
    )


def mark_assignment_handout_failed(
    *,
    binding_id,
    error,
):
    return mark_assignment_operation_failed(
        binding_id=binding_id,
        expected_state=(
            UserAssignmentBinding.State.EXTRACTING
        ),
        failed_state=(
            UserAssignmentBinding.State.HANDOUT_FAILED
        ),
        error=error,
    )


def mark_assignment_collection_complete(
    *,
    binding_id,
):
    return mark_assignment_operation_complete(
        binding_id=binding_id,
        expected_state=(
            UserAssignmentBinding.State.COMPRESSING
        ),
        completed_state=(
            UserAssignmentBinding.State.COLLECTED
        ),
    )


def mark_assignment_collection_failed(
    *,
    binding_id,
    error,
):
    return mark_assignment_operation_failed(
        binding_id=binding_id,
        expected_state=(
            UserAssignmentBinding.State.COMPRESSING
        ),
        failed_state=(
            UserAssignmentBinding.State.COLLECTION_FAILED
        ),
        error=error,
    )


def get_course_students(course):
    return (
        UserCourseBinding.objects
        .filter(
            course=course,
            is_teacher=False,
        )
        .select_related("user")
    )


def count_handout_candidates(assignment):
    student_ids = set(
        get_course_students(
            assignment.course
        ).values_list(
            "user_id",
            flat=True,
        )
    )

    existing = {
        binding.user_id: binding
        for binding in (
            UserAssignmentBinding.objects
            .filter(
                assignment=assignment,
                user_id__in=student_ids,
            )
            .only(
                "user_id",
                "state",
            )
        )
    }

    return sum(
        1
        for user_id in student_ids
        if (
            user_id not in existing
            or existing[user_id].state
            == UserAssignmentBinding.State.QUEUED
        )
    )


def count_collect_candidates(assignment):
    return (
        UserAssignmentBinding.objects
        .filter(
            assignment=assignment,
            state=(
                UserAssignmentBinding
                .State.WORKINPROGRESS
            ),
        )
        .count()
    )


def _handout_assignment(
    *,
    assignment,
):
    handed_out = []

    for course_binding in get_course_students(
        assignment.course
    ):
        binding, _ = (
            UserAssignmentBinding.objects
            .get_or_create(
                assignment=assignment,
                user=course_binding.user,
            )
        )

        if (
            binding.state
            != UserAssignmentBinding.State.QUEUED
        ):
            continue

        handed_out.append(
            queue_assignment_handout(
                binding=binding,
            )
        )

    return tuple(handed_out)


def handout_assignment_now(
    *,
    assignment,
    actor,
):
    assignment = (
        Assignment.objects
        .manageable_by(actor)
        .get(pk=assignment.pk)
    )

    return _handout_assignment(
        assignment=assignment,
    )


def handout_assignment_automatically(
    *,
    assignment,
):
    assignment = (
        Assignment.objects
        .select_related("course")
        .get(pk=assignment.pk)
    )

    return _handout_assignment(
        assignment=assignment,
    )


def _collect_assignment(
    *,
    assignment,
):
    bindings = (
        UserAssignmentBinding.objects
        .filter(
            assignment=assignment,
            state=UserAssignmentBinding.State.WORKINPROGRESS,
        )
    )

    return tuple(
        queue_assignment_collection(
            binding=binding,
            student_submission=False,
        )
        for binding in bindings
    )


def collect_assignment_now(
    *,
    assignment,
    actor,
):
    assignment = (
        Assignment.objects
        .manageable_by(actor)
        .get(pk=assignment.pk)
    )

    return _collect_assignment(
        assignment=assignment,
    )


def submit_assignment(
    *,
    binding,
    actor,
):
    binding = (
        UserAssignmentBinding.objects
        .get(
            pk=binding.pk,
            user=actor,
        )
    )

    return queue_assignment_collection(
        binding=binding,
        student_submission=True,
    )


def collect_assignment_automatically(
    *,
    assignment,
):
    assignment = Assignment.objects.get(
        pk=assignment.pk
    )

    return _collect_assignment(
        assignment=assignment,
    )



@transaction.atomic
def score_student_assignment(
    *,
    binding,
    actor,
    score,
    feedback,
):
    binding.finalize(
        actor,
        score,
        feedback,
    )


@transaction.atomic
def update_assignment_schedule(
    *,
    assignment,
    actor,
    field,
    value,
):
    assignment = (
        Assignment.objects
        .manageable_by(actor)
        .select_for_update()
        .get(pk=assignment.pk)
    )

    if field not in {
        "valid_from",
        "expires_at",
    }:
        raise AssignmentActionError(
            "Invalid assignment schedule field."
        )

    valid_from = assignment.valid_from
    expires_at = assignment.expires_at

    if field == "valid_from":
        valid_from = value
    else:
        expires_at = value

    if (
        valid_from is not None
        and expires_at is not None
        and valid_from >= expires_at
    ):
        raise AssignmentActionError(
            "The validity start must be before "
            "the expiry time."
        )

    setattr(
        assignment,
        field,
        value,
    )

    assignment.save(
        update_fields=[field]
    )

    return assignment


@transaction.atomic
def queue_assignment_collection(
    *,
    binding,
    student_submission=False,
):
    binding = (
        UserAssignmentBinding.objects
        .select_for_update()
        .get(pk=binding.pk)
    )

    if (
        binding.state
        != UserAssignmentBinding.State.WORKINPROGRESS
    ):
        raise AssignmentActionError(
            "This assignment cannot be collected "
            f"from state {binding.get_state_display()}."
        )

    binding.last_submitted_at = timezone.now()
    binding.state = (
        UserAssignmentBinding.State.COMPRESSING
    )

    update_fields = [
        "last_submitted_at",
        "state",
        "last_operation_error",
        "last_operation_failed_at",
    ]

    if student_submission:
        binding.submit_count += 1
        update_fields.append("submit_count")

    clear_operation_error(binding)

    binding.save(
        update_fields=update_fields,
    )

    binding_id = binding.pk

    logger.debug(
        "Registering assignment_collect on_commit binding=%s",
        binding_id,
    )


    def enqueue():
        from ..tasks import assignment_collect

        logger.debug(
            "Enqueueing assignment_collect binding=%s",
            binding_id,
        )

        assignment_collect(binding_id)

    transaction.on_commit(enqueue)

    return binding_id


@transaction.atomic
def queue_assignment_handout(
    *,
    binding,
):
    binding = (
        UserAssignmentBinding.objects
        .select_for_update()
        .get(pk=binding.pk)
    )

    if (
        binding.state
        != UserAssignmentBinding.State.QUEUED
    ):
        raise AssignmentActionError(
            "This assignment cannot be handed out "
            f"from state {binding.get_state_display()}."
        )

    binding.last_received_at = timezone.now()
    binding.state = (
        UserAssignmentBinding.State.EXTRACTING
    )

    clear_operation_error(binding)

    binding.save(
        update_fields=[
            "last_received_at",
            "state",
            "last_operation_error",
            "last_operation_failed_at",            
        ]
    )

    binding_id = binding.pk

    logger.debug(
        "Registering assignment_handout on_commit binding=%s",
        binding_id,
    )

    def enqueue():
        from education.tasks import (
            assignment_handout,
        )

        logger.debug(
            "Enqueueing assignment_handout binding=%s",
            binding_id,
        )

        assignment_handout(binding_id)

    transaction.on_commit(enqueue)

    return binding_id


