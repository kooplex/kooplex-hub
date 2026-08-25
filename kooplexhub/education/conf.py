from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from hub.confutils import merge_dataclass
from hub.conf_types import (
    MountSettings,
    ArchivableMountSettings,
    TreeMountSettings,
    ArchivableTreeMountSettings
)


@dataclass(frozen=True)
class AssignmentMountSettings(MountSettings):
    snapshot: str
    collection: str
    feedback: str



def _default_public_mount():
    return ArchivableMountSettings(
        claim="education",
        subpath="public",
        folder="{course.folder}/public",
        mountpoint="/course/{course.folder}.public",
        mountpoint_hub="/mnt/course_public",
        archive_name="public-{course.folder}.{time}.tar.gz",
    )

def _default_prepare_mount():
    return ArchivableMountSettings(
        claim="education",
        subpath="assignment_prepare",
        folder="{course.folder}",
        mountpoint="/course/{course.folder}.assignment_prepare",
        mountpoint_hub="/mnt/assignment_prepare",
        archive_name="prepare-{course.folder}.{time}.tar.gz",
    )

def _default_workdir_mount():
    return ArchivableTreeMountSettings(
        claim="education",
        subpath="workdir",
        folder_top="{course.folder}",
        folder="{course.folder}/{user.username}",
        mountpoint="/course/{course.folder}",
        mountpoint_hub="/mnt/course_workdir",
        archive_name="{user.username}/workdir-{course.folder}-{user.username}.{time}.tar.gz",
    )

def _default_snapshot_mount():
    return MountSettings(
        claim="education",
        subpath="assignment_snapshot",
        folder="{course.folder}",
        mountpoint="/course/{course.folder}.assignment_snapshot",
        mountpoint_hub="/mnt/assignment_snapshot",
    )
#    snapshot: str = "snapshot-{assignment._safename}.{time}.tar.gz"
#    collection: str = "collection-{assignment._safename}-{user.username}.{time}.tar.gz"
#    feedback: str = "feedback-{assignment._safename}-{user.username}.{time}.tar.gz"

def _default_assignment_mount():
    return ArchivableTreeMountSettings(
        claim="education",
        subpath="assignment",
        folder_top="{course.folder}",
        folder="{course.folder}/{user.username}",
        mountpoint="/assignment/{course.folder}.assignment",
        mountpoint_hub="/mnt/course_assignment",
        archive_name="{user.username}/assignment-{course.folder}-{assignment._safename}-{user.username}.{time}.tar.gz",
    )

def _default_correct_mount():
    return TreeMountSettings(
        claim="education",
        subpath="assignment_correct",
        folder_top="{course.folder}",
        folder="{course.folder}/{user.username}",
        mountpoint="/course/{course.folder}.correct",
        mountpoint_hub="/mnt/assignment_correct",
    )

@dataclass(frozen=True)
class MountsSettings:
    public: ArchivableMountSettings = field(
        default_factory=_default_public_mount
    )
    prepare: ArchivableMountSettings = field(
        default_factory=_default_prepare_mount
    )
    workdir: ArchivableTreeMountSettings = field(
        default_factory=_default_workdir_mount
    )
    snapshot: MountSettings = field(
        default_factory=_default_snapshot_mount
    )
    assignment: ArchivableTreeMountSettings = field(
        default_factory=_default_assignment_mount
    )
    correct: TreeMountSettings = field(
        default_factory=_default_correct_mount
    )

#from .models import (
#    Course, 
#    UserCourseBinding,
#)


@dataclass(frozen=True)
class MembershipEditorSettings:
    search_limit: int = 12
    minimum_query_length: int = 2


#@dataclass(frozen=True)
#class CoursePresentationSettings:
#    scope_icons: dict = field(
#        default_factory=lambda: {
#            Course.Scope.PUBLIC: "bi-globe",
#            Course.Scope.INTERNAL: "bi-people",
#            Course.Scope.PRIVATE: "bi-lock",
#        }
#    )
#
#    member_role_icons: dict = field(
#        default_factory=lambda: {
#            UserCourseBinding.Role.CREATOR: (
#                "bi-person-badge"
#            ),
#            UserCourseBinding.Role.ADMIN: (
#                "bi-shield-lock"
#            ),
#            UserCourseBinding.Role.COLLABORATOR: (
#                "bi-person"
#            ),
#        }
#    )


@dataclass(frozen=True)
class EducationSettings:
    membership_editor: MembershipEditorSettings = field(
        default_factory=MembershipEditorSettings
    )
    mounts: MountsSettings = field(
        default_factory=MountsSettings
    )
#    presentation: CoursePresentationSettings = field(
#        default_factory=CoursePresentationSettings
#    )
#    skip_workflow_chooser_when_no_joinable_project: bool = True



EDUCATION_SETTINGS = merge_dataclass(
    EducationSettings(),
    getattr(settings, "EDUCATION", {}),
)

