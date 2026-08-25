from django.core.management.base import BaseCommand, CommandError

from hub.services.directory import (
    DirectoryProvisioningError,
    DirectoryService,
)


class Command(BaseCommand):
    help = "Initialize the LDAP directory structure required by Kooplex."

    def handle(self, *args, **options):
        directory = DirectoryService()

        status = directory.check_structure()

        self.stdout.write("LDAP directory status:")
        self.stdout.write(
            f"  base:   {'OK' if status.base_exists else 'MISSING'}"
        )
        self.stdout.write(
            f"  users:  {'OK' if status.users_exists else 'MISSING'}"
        )
        self.stdout.write(
            f"  groups: {'OK' if status.groups_exists else 'MISSING'}"
        )

        if status.ready:
            self.stdout.write(
                self.style.SUCCESS(
                    "LDAP directory structure is already initialized."
                )
            )
            return

        try:
            created = directory.ensure_structure()
        except DirectoryProvisioningError as exc:
            raise CommandError(str(exc)) from exc

        if created:
            self.stdout.write("Created:")
            for dn in created:
                self.stdout.write(f"  {dn}")

        self.stdout.write(
            self.style.SUCCESS(
                "LDAP directory structure is ready."
            )
        )

