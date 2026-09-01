from dataclasses import dataclass, field

from django.db import transaction

from hub.models import Group
from hub.services.groups import (
    add_user_to_group,
    ensure_group,
)

from project.models import (
    Project,
    UserProjectBinding,
)
from project.services.provisioning import (
    project_group_name,
)


@dataclass(frozen=True)
class ProjectReconcileIssue:
    project_id: int
    project_name: str
    issue: str


@dataclass
class ProjectReconcileResult:
    inspected: int = 0

    missing_groups: list = field(
        default_factory=list
    )

    wrong_groups: list = field(
        default_factory=list
    )

    missing_memberships: list = field(
        default_factory=list
    )

    skipped: list = field(
        default_factory=list
    )

    groups_attached: list = field(
        default_factory=list
    )

    memberships_repaired: list = field(
        default_factory=list
    )


class ProjectReconciler:
    def inspect_project(
        self,
        project,
        result,
    ):
        result.inspected += 1

        if not project.subpath:
            result.skipped.append(
                ProjectReconcileIssue(
                    project_id=project.pk,
                    project_name=project.name,
                    issue="Project has no subpath.",
                )
            )
            return

        expected_name = (
            project_group_name(project)
        )

        if project.group_id is None:
            result.missing_groups.append(
                ProjectReconcileIssue(
                    project_id=project.pk,
                    project_name=project.name,
                    issue=(
                        f"Missing project group; "
                        f"expected {expected_name!r}."
                    ),
                )
            )

        elif project.group.name != expected_name:
            result.wrong_groups.append(
                ProjectReconcileIssue(
                    project_id=project.pk,
                    project_name=project.name,
                    issue=(
                        f"Attached group is "
                        f"{project.group.name!r}; "
                        f"expected {expected_name!r}."
                    ),
                )
            )

        if project.group_id is None:
            return

        member_ids = set(
            project.userbindings.values_list(
                "user_id",
                flat=True,
            )
        )

        group_member_ids = set(
            project.group.userbindings
            .values_list(
                "user_id",
                flat=True,
            )
        )

        for missing_user_id in (
            member_ids - group_member_ids
        ):
            binding = (
                project.userbindings
                .select_related("user")
                .get(user_id=missing_user_id)
            )

            result.missing_memberships.append(
                ProjectReconcileIssue(
                    project_id=project.pk,
                    project_name=project.name,
                    issue=(
                        f"{binding.user.username} "
                        "is a Project member but "
                        "not a Project-group member."
                    ),
                )
            )

    def repair_project(
            self,
            project,
            result,
        ):
            if not project.subpath:
                return
    
            expected_name = (
                project_group_name(project)
            )
    
            group = ensure_group(
                name=expected_name,
                grouptype=Group.TP_PROJECT,
            )
    
            if project.group_id != group.pk:
                Project.objects.filter(
                    pk=project.pk,
                ).update(
                    group=group,
                )
    
                project.group = group
    
                result.groups_attached.append(
                    (
                        project.pk,
                        group.name,
                    )
                )
    
            members = (
                project.userbindings
                .select_related("user")
                .all()
            )
    
            for binding in members:
                add_user_to_group(
                    user=binding.user,
                    group=group,
                )
    
                result.memberships_repaired.append(
                    (
                        project.pk,
                        binding.user.username,
                        group.name,
                    )
                )
    
    def inspect(
        self,
        projects,
    ):
        result = ProjectReconcileResult()

        for project in projects:
            self.inspect_project(
                project,
                result,
            )

        return result

    def repair(
        self,
        projects,
    ):
        result = ProjectReconcileResult()

        for project in projects:
            self.repair_project(
                project,
                result,
            )

        return result

