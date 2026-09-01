from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from hub.services.directory import (
    DirectoryService,
)
from hub.services.directory_reconcile import (
    DirectoryReconciler,
)

class Command(BaseCommand):
    help = (
        "Compare the Kooplex database with LDAP "
        "users, groups and memberships."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help=(
                "Create safely repairable missing "
                "LDAP groups and memberships."
            ),
        )

        parser.add_argument(
            "--fix-delete-ldaponly-groups",
            action="store_true",
            help=(
                "Delete LDAP groups that have no corresponding "
                "Django Group. Requires --fix."
            ),
        )
    
        parser.add_argument(
            "--fix-delete-ldaponly-users",
            action="store_true",
            help=(
                "Delete LDAP users that have no corresponding "
                "Django User. Requires --fix."
            ),
        )

    def handle(self, *args, **options):
        directory = DirectoryService()

        status = directory.check_structure()

        if not status.ready:
            raise CommandError(
                "LDAP directory structure is not ready. "
                "Run `python manage.py ldap_init` first."
            )

        reconciler = DirectoryReconciler()
        diff = reconciler.inspect()

        self._print_diff(diff)

        if (
            options["fix_delete_ldaponly_groups"]
            or options["fix_delete_ldaponly_users"]
        ) and not options["fix"]:
            raise CommandError(
                "LDAP deletion options require --fix."
            )

        if not options["fix"]:
            if diff.consistent:
                self.stdout.write(
                    self.style.SUCCESS(
                        "LDAP and Hub are consistent."
                    )
                )
            else:
                self.stdout.write("")
                self.stdout.write(
                    "Dry run only. Use --fix to repair "
                    "safe discrepancies."
                )

            return

        result = reconciler.repair(
            diff,
            delete_ldap_only_groups=(
                options["fix_delete_ldaponly_groups"]
            ),
            delete_ldap_only_users=(
                options["fix_delete_ldaponly_users"]
            ),
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Repair pass complete."
            )
        )

        if result.groups_created:
            self.stdout.write(
                "Groups created:"
            )
            for name in result.groups_created:
                self.stdout.write(
                    f"  + {name}"
                )

        if result.memberships_created:
            self.stdout.write(
                "Memberships created:"
            )

            for item in (
                result.memberships_created
            ):
                self.stdout.write(
                    f"  + {item.username}"
                    f" -> {item.group_name}"
                )

        if result.users_skipped:
            self.stdout.write(
                self.style.WARNING(
                    "Missing LDAP users require "
                    "manual/identity reconciliation:"
                )
            )

            for username in (
                result.users_skipped
            ):
                self.stdout.write(
                    f"  ! {username}"
                )

        if result.profile_identities_repaired:
            self.stdout.write(
                "Profile identities repaired:"
            )
        
            for username in (
                result.profile_identities_repaired
            ):
                self.stdout.write(
                    f"  + {username}"
                )
        
        if result.profile_identities_skipped:
            self.stdout.write(
                self.style.WARNING(
                    "Profile identities skipped:"
                )
            )
        
            for username in (
                result.profile_identities_skipped
            ):
                self.stdout.write(
                    f"  ! {username}"
                )


    def _print_diff(self, diff):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "LDAP consistency report"
            )
        )

        self._section(
            "Missing LDAP users",
            diff.missing_users,
        )

        self._section(
            "LDAP-only users",
            diff.ldap_only_users,
        )

        self._section(
            "Missing LDAP groups",
            diff.missing_groups,
        )

        self._section(
            "LDAP-only groups",
            diff.ldap_only_groups,
        )

        if diff.gid_mismatches:
            self.stdout.write(
                "\nGID mismatches:"
            )

            for mismatch in (
                diff.gid_mismatches
            ):
                self.stdout.write(
                    "  ! "
                    f"{mismatch.group_name}: "
                    f"DB={mismatch.database_gid}, "
                    f"LDAP={mismatch.ldap_gid}"
                )

        if diff.missing_memberships:
            self.stdout.write(
                "\nMissing LDAP memberships:"
            )

            for item in (
                diff.missing_memberships
            ):
                self.stdout.write(
                    f"  + {item.username}"
                    f" -> {item.group_name}"
                )

        if diff.ldap_only_memberships:
            self.stdout.write(
                "\nLDAP-only memberships:"
            )

            for item in (
                diff.ldap_only_memberships
            ):
                self.stdout.write(
                    f"  ? {item.username}"
                    f" -> {item.group_name}"
                )

        if diff.missing_profiles:
            self.stdout.write(
                "\nUsers without Profile:"
            )
        
            for item in diff.missing_profiles:
                self.stdout.write(
                    f"  ! {item.username}"
                )
        
        if diff.profile_identity_missing:
            self.stdout.write(
                "\nProfile identities missing:"
            )
        
            for item in (
                diff.profile_identity_missing
            ):
                self.stdout.write(
                    "  + "
                    f"{item.username}: "
                    f"DB uid={item.database_uid}, "
                    f"gid={item.database_gid}; "
                    f"LDAP uid={item.ldap_uid}, "
                    f"gid={item.ldap_gid}"
                )
        
        if diff.profile_identity_mismatches:
            self.stdout.write(
                self.style.WARNING(
                    "\nProfile/LDAP identity mismatches:"
                )
            )
        
            for item in (
                diff.profile_identity_mismatches
            ):
                self.stdout.write(
                    "  ! "
                    f"{item.username}: "
                    f"DB uid={item.database_uid}, "
                    f"gid={item.database_gid}; "
                    f"LDAP uid={item.ldap_uid}, "
                    f"gid={item.ldap_gid}"
                )


    def _section(
        self,
        title,
        values,
    ):
        if not values:
            return

        self.stdout.write(f"\n{title}:")

        for value in values:
            self.stdout.write(
                f"  {value}"
            )

