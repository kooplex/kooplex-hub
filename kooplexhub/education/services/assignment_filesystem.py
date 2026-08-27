import logging
import os

from ..models import (
    UserAssignmentBinding,
)
from ..filesystem import (
    assignment_workdir,
    assignment_collection_archive,
    assignment_correct_dir,
)
from hub.lib import (
    archive_directory,
    extract_tarball,
    grantaccess_group,
    grantaccess_user,
)
from .assignments import (
    mark_assignment_preparation_complete,
    mark_assignment_preparation_failed,
    mark_assignment_handout_complete,
    mark_assignment_handout_failed,
    mark_assignment_collection_complete,
    mark_assignment_collection_failed,
)


logger = logging.getLogger(__name__)


def perform_assignment_snapshot(
    *,
    assignment_id,
):
    assignment = (
        Assignment.objects
        .select_related(
            "course",
            "creator",
        )
        .get(pk=assignment_id)
    )

    if (
        assignment.state
        != Assignment.State.PREPARING
    ):
        logger.warning(
            "Ignoring assignment snapshot %s "
            "in state %s",
            assignment.pk,
            assignment.state,
        )
        return

    try:
        source = assignment_source(
            assignment
        )

        logger.debug(
            "Assignment %s snapshot: %s -> %s",
            assignment.pk,
            source,
            assignment.filename,
        )

        archive_directory(
            source,
            assignment.filename,
            remove=False,
        )

        if not os.path.isfile(
            assignment.filename
        ):
            raise RuntimeError(
                "Assignment snapshot archive "
                f"was not created: "
                f"{assignment.filename}"
            )

    except Exception as error:
        mark_assignment_preparation_failed(
            assignment_id=assignment.pk,
            error=error,
        )

        logger.exception(
            "Assignment snapshot failed "
            "assignment=%s",
            assignment.pk,
        )

        raise

    mark_assignment_preparation_complete(
        assignment_id=assignment.pk,
    )


def _perform_assignment_handout_filesystem(
    binding,
):
    logger.debug(
        "Assignment handout %s: archive start",
        binding.pk,
    )

    folder = assignment_workdir(binding)

    extract_tarball(
        binding.assignment.filename,
        folder,
    )

    if not os.path.isdir(folder):
        raise RuntimeError(
            "Assignment working directory "
            f"was not created: {folder}"
        )

    teachers = (
        binding.assignment.course.group_teachers
    )
    students = (
        binding.assignment.course.group_students
    )

    grantaccess_group(
        teachers,
        folder,
        readonly=True,
        recursive=True,
        follow=True,
    )

    grantaccess_user(
        binding.user,
        folder,
        readonly=False,
        recursive=True,
        follow=False,
    )

    grantaccess_user(
        binding.user,
        folder,
        readonly=False,
        recursive=True,
        follow=True,
    )


def _perform_assignment_collection_filesystem(
    binding,
):
    logger.debug(
        "Assignment collection %s: archive start",
        binding.pk,
    )

    folder = assignment_workdir(binding)

    archive = assignment_collection_archive(
        binding
    )

    correction_dir = assignment_correct_dir(
        binding
    )

    archive_directory(
        folder,
        archive,
        remove=(
            binding.assignment.remove_collected
        ),
    )

    if not os.path.isfile(archive):
        raise RuntimeError(
            f"Assignment archive was not created: {archive}"
        )

    extract_tarball(
        archive,
        correction_dir,
    )

    if not os.path.isdir(correct_dir):
        raise RuntimeError(
            "Assignment correction directory "
            f"was not created: {correct_dir}"
        )

    grantaccess_group(
        binding.assignment.course.group_teachers,
        correction_dir,
        readonly=False,
    )


def perform_assignment_handout(
    *,
    binding_id,
):
    binding = (
        UserAssignmentBinding.objects
        .select_related(
            "user",
            "assignment",
            "assignment__course",
            "assignment__course__group_students",
            "assignment__course__group_teachers",
        )
        .get(pk=binding_id)
    )

    if (
        binding.state
        != UserAssignmentBinding.State.EXTRACTING
    ):
        logger.warning(
            "Ignoring assignment handout %s "
            "in state %s",
            binding.pk,
            binding.state,
        )
        return

    try:
        _perform_assignment_handout_filesystem(
            binding
        )

    except Exception as error:
        mark_assignment_handout_failed(
            binding_id=binding.pk,
            error=error,
        )

        logger.exception(
            "Assignment handout failed "
            "for binding %s",
            binding.pk,
        )

        raise

    mark_assignment_handout_complete(
        binding_id=binding.pk,
    )        



def perform_assignment_collection(
    *,
    binding_id,
):
    binding = (
        UserAssignmentBinding.objects
        .select_related(
            "user",
            "assignment",
            "assignment__course",
            "assignment__course__group_teachers",
        )
        .get(pk=binding_id)
    )

    if (
        binding.state
        != UserAssignmentBinding.State.COMPRESSING
    ):
        logger.warning(
            "Ignoring assignment collection %s "
            "in state %s",
            binding.pk,
            binding.state,
        )
        return

    try:
        _perform_assignment_collection_filesystem(
            binding
        )

    except Exception as error:
        mark_assignment_collection_failed(
            binding_id=binding.pk,
            error=error,
        )

        logger.exception(
            "Assignment collection failed "
            "for binding %s",
            binding.pk,
        )

        raise

    mark_assignment_collection_complete(
        binding_id=binding.pk,
    )

