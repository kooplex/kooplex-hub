import os
from dataclasses import dataclass

from hub.lib import grantaccess_group
from hub.lib.filesystem import _mkdir
from hub.models import Group

from ..filesystem import (
    course_public,
    course_assignment_prepare_root,
    course_assignment_snapshot,
    course_assignment_root,
    assignment_correct_root,
)

from hub.services.groups import ensure_group


@dataclass(frozen=True)
class CourseInfrastructure:
    student_group: object
    teacher_group: object


@dataclass(frozen=True, slots=True)
class CourseFilesystemStatus:
    public: bool
    prepare: bool
    snapshot: bool
    assignments: bool
    corrections: bool

    @property
    def ready(self):
        return all((
            self.public,
            self.prepare,
            self.snapshot,
            self.assignments,
            self.corrections,
        ))

    @property
    def missing(self):
        result = []

        if not self.public:
            result.append("public")
        if not self.prepare:
            result.append("prepare")
        if not self.snapshot:
            result.append("snapshot")
        if not self.assignments:
            result.append("assignments")
        if not self.corrections:
            result.append("corrections")

        return tuple(result)


def inspect_course_filesystem(
    *,
    course,
):
    return CourseFilesystemStatus(
        public=os.path.isdir(
            course_public(course)
        ),
        prepare=os.path.isdir(
            course_assignment_prepare_root(course)
        ),
        snapshot=os.path.isdir(
            course_assignment_snapshot(course)
        ),
        assignments=os.path.isdir(
            course_assignment_root(course)
        ),
        corrections=os.path.isdir(
            assignment_correct_root(course)
        ),
    )


def provision_course_infrastructure(*, folder):
    """
    Create/resolve the two backing groups for a new course.

    Does not create the Course itself.
    """

    student_group = ensure_group(
        name=folder,
        grouptype=Group.TP_COURSE,
    )

    teacher_group = ensure_group(
        name=f"t-{folder}",
        grouptype=Group.TP_COURSE,
    )

    return CourseInfrastructure(
        student_group=student_group,
        teacher_group=teacher_group,
    )


def provision_course_filesystem(*, course):
    """
    Replaces the filesystem part of Course.pre_save.
    """

    student_group = course.group_students
    teacher_group = course.group_teachers

    public = course_public(course)
    _mkdir(public)

    grantaccess_group(
        student_group,
        public,
        readonly=True,
    )

    grantaccess_group(
        teacher_group,
        public,
        readonly=False,
    )

    prepare = course_assignment_prepare_root(course)
    _mkdir(prepare)

    grantaccess_group(
        teacher_group,
        prepare,
        readonly=False,
    )

    _mkdir(
        course_assignment_snapshot(course)
    )

    assignments = course_assignment_root(course)
    _mkdir(assignments)

    grantaccess_group(
        student_group,
        assignments,
        readonly=True,
    )

    grantaccess_group(
        teacher_group,
        assignments,
        readonly=True,
    )

    corrections = assignment_correct_root(course)
    _mkdir(corrections)

    grantaccess_group(
        teacher_group,
        corrections,
        readonly=True,
    )




