from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from hub.models import Profile
from hub.services.user_reconcile import (
    reconcile_user,
)


class Command(BaseCommand):
    help = (
        "Inspect and safely repair complete "
        "Kooplex user provisioning state."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--fix",
            action="store_true",
            help=(
                "Repair safe provisioning "
                "differences and mark verified "
                "Profiles READY."
            ),
        )

        parser.add_argument(
            "--user",
            default=None,
            help=(
                "Restrict reconciliation to "
                "one username."
            ),
        )

    def handle(
        self,
        *args,
        **options,
    ):
        queryset = (
            Profile.objects
            .select_related("user")
            .filter(
                user__is_superuser=False
            )
            .order_by(
                "user__username"
            )
        )

        username = options["user"]

        if username:
            queryset = queryset.filter(
                user__username=username
            )

            if not queryset.exists():
                raise CommandError(
                    f"User {username!r} has "
                    "no Profile."
                )

        fix = options["fix"]

        bad = 0

        for profile in queryset:
            try:
                status = reconcile_user(
                    profile=profile,
                    fix=fix,
                )

            except Exception as error:
                bad += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"{profile.user.username}: "
                        f"ERROR: {error}"
                    )
                )

                continue

            profile.refresh_from_db()

            if status.ready:
                marker = (
                    self.style.SUCCESS("READY")
                )

            else:
                bad += 1
                marker = (
                    self.style.WARNING(
                        "NOT READY"
                    )
                )

            self.stdout.write(
                f"{profile.user.username}: "
                f"{marker} "
                f"(state="
                f"{profile.get_state_display()})"
            )

            for problem in status.problems:
                self.stdout.write(
                    f"    - {problem}"
                )

        if not fix and bad:
            self.stdout.write("")
            self.stdout.write(
                "Dry run only. Use --fix to "
                "repair safe discrepancies."
            )


