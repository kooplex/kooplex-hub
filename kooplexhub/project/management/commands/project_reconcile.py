from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from project.models import Project
from project.services.reconcile import (
    ProjectReconciler,
)


class Command(BaseCommand):
    help = (
        "Inspect and safely repair Project "
        "group and membership consistency."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--fix",
            action="store_true",
            help=(
                "Repair safe missing Project "
                "groups and memberships."
            ),
        )

        parser.add_argument(
            "--project",
            type=int,
            default=None,
            help=(
                "Restrict reconciliation to "
                "one Project ID."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        queryset = (
            Project.objects
            .select_related("group")
            .prefetch_related(
                "userbindings__user",
            )
            .order_by("pk")
        )

        project_id = options["project"]

        if project_id is not None:
            queryset = queryset.filter(
                pk=project_id
            )

            if not queryset.exists():
                raise CommandError(
                    f"Project #{project_id} "
                    "does not exist."
                )

        reconciler = ProjectReconciler()

        result = reconciler.inspect(
            queryset
        )

        self._print_result(result)

        if not options["fix"]:
            if (
                result.missing_groups
                or result.wrong_groups
                or result.missing_memberships
                or result.skipped
            ):
                self.stdout.write("")
                self.stdout.write(
                    "Dry run only. Use --fix "
                    "to repair safe discrepancies."
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "Projects are consistent."
                    )
                )

            return

        fixed = reconciler.repair(
            queryset
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Project repair pass complete."
            )
        )

        self._print_repairs(fixed)

    def _print_result(
        self,
        result,
    ):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Project consistency report"
            )
        )

        self.stdout.write(
            f"Projects inspected: "
            f"{result.inspected}"
        )

        sections = (
            (
                "Missing Project groups",
                result.missing_groups,
            ),
            (
                "Incorrect Project groups",
                result.wrong_groups,
            ),
            (
                "Missing group memberships",
                result.missing_memberships,
            ),
            (
                "Skipped",
                result.skipped,
            ),
        )

        for title, items in sections:
            if not items:
                continue

            self.stdout.write("")
            self.stdout.write(title + ":")

            for item in items:
                self.stdout.write(
                    f"  Project #{item.project_id} "
                    f"{item.project_name!r}: "
                    f"{item.issue}"
                )

    def _print_repairs(
        self,
        result,
    ):
        for project_id, group_name in (
            result.groups_attached
        ):
            self.stdout.write(
                f"  + Project #{project_id} "
                f"-> {group_name}"
            )

        for (
            project_id,
            username,
            group_name,
        ) in result.memberships_repaired:
            self.stdout.write(
                f"  + Project #{project_id}: "
                f"{username} -> {group_name}"
            )


