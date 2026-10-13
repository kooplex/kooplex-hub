import shlex
import time
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from container.models import Container
from container.services.image_catalog import ImageCatalogService
from container.services.lifecycle import (
    create_container,
    delete_container,
)
from container.services.runtime_control import (
    request_start,
    request_stop,
)
from container.services.kubernetes.labels import workload_labels
from container.services.kubernetes.wiring import build_pod_operations

from volume.conf import VOLUME_SETTINGS
from volume.models import Volume
from volume.services.lifecycle import (
    create_attachment,
    delete_attachment,
)
from volume.services.provisioning import attachment_host_path


User = get_user_model()


def wait_for_volume_ready(volume, *, timeout=180, interval=0.5):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        volume.refresh_from_db()

        if volume.provisioning_state == Volume.ProvisioningState.READY:
            return volume

        if volume.provisioning_state == Volume.ProvisioningState.FAILED:
            raise CommandError(
                f"Attachment #{volume.pk} failed provisioning: "
                f"{volume.last_operation_error}"
            )

        time.sleep(interval)

    raise CommandError(
        f"Timed out waiting for attachment #{volume.pk}; "
        f"state={volume.provisioning_state}, "
        f"error={volume.last_operation_error!r}"
    )


def wait_for_volume_deleted(volume_id, *, timeout=180, interval=0.5):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        volume = Volume.objects.filter(pk=volume_id).first()

        if volume is None:
            return

        if volume.provisioning_state == Volume.ProvisioningState.FAILED:
            raise CommandError(
                f"Attachment #{volume_id} deletion failed: "
                f"{volume.last_operation_error}"
            )

        time.sleep(interval)

    volume = Volume.objects.filter(pk=volume_id).first()

    raise CommandError(
        f"Timed out waiting for attachment #{volume_id} deletion; "
        f"state={getattr(volume, 'provisioning_state', None)}, "
        f"error={getattr(volume, 'last_operation_error', '')!r}"
    )


def wait_for_container_state(
    container,
    *,
    success,
    failure=(),
    timeout=180,
    interval=0.5,
):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        container.refresh_from_db()

        if container.state in success:
            return container

        if container.state in failure:
            raise CommandError(
                f"Environment #{container.pk} entered "
                f"{container.state}: "
                f"{container.state_backend or ''}"
            )

        time.sleep(interval)

    raise CommandError(
        f"Timed out waiting for environment #{container.pk}; "
        f"state={container.state}, "
        f"backend={container.state_backend!r}"
    )


class Command(BaseCommand):
    help = "Run an end-to-end attachment lifecycle smoke test."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            required=True,
            help="Attachment owner username.",
        )
        parser.add_argument(
            "--user2",
            default=None,
            help="Optional second user used to verify public RO access.",
        )
        parser.add_argument(
            "--image",
            default=None,
            help="Image ID or exact image name.",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=180,
        )

    def step(self, text):
        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f">>> {text}"
            )
        )

    def resolve_user(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(
                f"User {username!r} does not exist."
            ) from exc

    def resolve_image(self, user, value):
        images = ImageCatalogService.available_for_user(user)

        if value is None:
            image = images.first()

        elif str(value).isdigit():
            image = images.filter(pk=int(value)).first()

        else:
            image = images.filter(name=value).first()

        if image is None:
            raise CommandError(
                f"No matching image is available for {user.username!r}."
            )

        return image

    def start_container(self, container, user, timeout):
        request_start(
            container=container,
            actor=user,
        )

        wait_for_container_state(
            container,
            success={
                Container.State.RUNNING,
                Container.State.NEED_RESTART,
            },
            failure={
                Container.State.ERROR,
            },
            timeout=timeout,
        )

    def stop_and_delete_container(self, container, user, timeout):
        if container is None:
            return

        container.refresh_from_db()

        if container.state != Container.State.NOTPRESENT:
            request_stop(
                container=container,
                actor=user,
            )

            wait_for_container_state(
                container,
                success={
                    Container.State.NOTPRESENT,
                },
                failure={
                    Container.State.ERROR,
                },
                timeout=timeout,
            )

        delete_container(
            container=container,
            actor=user,
        )

    def handle(self, *args, **options):
        timeout = options["timeout"]

        user = self.resolve_user(options["user"])
        user2 = (
            self.resolve_user(options["user2"])
            if options["user2"]
            else None
        )

        image1 = self.resolve_image(
            user,
            options["image"],
        )

        image2 = (
            self.resolve_image(
                user2,
                options["image"],
            )
            if user2
            else None
        )

        token = uuid.uuid4().hex[:8]
        folder = f"smoke{token}"

        attachment = None
        container1 = None
        container2 = None

        try:
            self.step("Creating attachment")

            attachment = create_attachment(
                user=user,
                folder=folder,
                description="Attachment smoke test",
            )

            self.stdout.write(
                f"Attachment #{attachment.pk}: "
                f"{attachment.folder}"
            )

            wait_for_volume_ready(
                attachment,
                timeout=timeout,
            )

            attachment.refresh_from_db()

            self.stdout.write(
                self.style.SUCCESS(
                    "Attachment READY"
                )
            )

            self.step("Populating attachment from hub")

            host_path = attachment_host_path(
                attachment
            )

            marker_path = host_path / "smoke.txt"
            marker_path.write_text(
                token + "\n",
                encoding="utf-8",
            )

            self.stdout.write(
                f"Wrote {marker_path}"
            )

            mount_path = (
                VOLUME_SETTINGS.mountpoint.format(
                    volume=attachment,
                )
            )

            self.step("Creating owner environment")

            container1 = create_container(
                user=user,
                image=image1,
                name=f"attachment-smoke-{token}",
                volume_ids=[attachment.pk],
            )

            self.start_container(
                container1,
                user,
                timeout,
            )

            pod_operations = build_pod_operations()

            pod = pod_operations.current_pod(
                workload_labels(container1)
            )

            if pod is None:
                raise CommandError(
                    "Owner environment is running "
                    "but Kubernetes pod is missing."
                )

            self.step("Checking owner read access")

            output = pod_operations.exec_for_container(
                container1,
                (
                    f"cat "
                    f"{shlex.quote(mount_path + '/smoke.txt')}"
                ),
            )

            if output.strip() != token:
                raise CommandError(
                    f"Unexpected owner read result: {output!r}"
                )

            self.step("Checking owner write access")

            owner_write = (
                mount_path + "/owner-write.txt"
            )

            output = pod_operations.exec_for_container(
                container1,
                (
                    f"printf '%s\\n' {shlex.quote(token)} "
                    f"> {shlex.quote(owner_write)}; "
                    f"cat {shlex.quote(owner_write)}"
                ),
            )

            if output.strip() != token:
                raise CommandError(
                    "Attachment owner could not write."
                )

            if user2 is not None:
                self.step(
                    "Checking attachment visibility for user2"
                )

                if not (
                    Volume.objects
                    .attachable_by(user2)
                    .filter(pk=attachment.pk)
                    .exists()
                ):
                    raise CommandError(
                        "Attachment is not attachable by user2."
                    )

                self.step("Creating user2 environment")

                container2 = create_container(
                    user=user2,
                    image=image2,
                    name=f"attachment-smoke-{token}",
                    volume_ids=[attachment.pk],
                )

                self.start_container(
                    container2,
                    user2,
                    timeout,
                )

                self.step("Checking user2 read access")

                output = (
                    pod_operations
                    .exec_for_container(
                        container2,
                        (
                            f"cat "
                            f"{shlex.quote(mount_path + '/smoke.txt')}"
                        ),
                    )
                )

                if output.strip() != token:
                    raise CommandError(
                        f"user2 read failed: {output!r}"
                    )

                self.step("Checking user2 read-only mount")

                probe = (
                    mount_path
                    + "/user2-write-test"
                )

                output = (
                    pod_operations
                    .exec_for_container(
                        container2,
                        (
                            f"if touch {shlex.quote(probe)} "
                            "2>/dev/null; "
                            "then echo WRITABLE; "
                            "else echo READONLY; fi"
                        ),
                    )
                )

                if "READONLY" not in output:
                    raise CommandError(
                        "Attachment is writable by user2."
                    )

            self.step("Stopping environments")

            if container2 is not None:
                self.stop_and_delete_container(
                    container2,
                    user2,
                    timeout,
                )
                container2 = None

            self.stop_and_delete_container(
                container1,
                user,
                timeout,
            )
            container1 = None

            self.step("Deleting attachment")

            attachment_id = delete_attachment(
                attachment=attachment,
                actor=user,
            )

            wait_for_volume_deleted(
                attachment_id,
                timeout=timeout,
            )

            if host_path.exists():
                raise CommandError(
                    "Attachment DB row disappeared "
                    "but storage directory still exists."
                )

            attachment = None

        except Exception:
            self.stderr.write(
                self.style.ERROR(
                    "\nATTACHMENT SMOKE FAILED"
                )
            )

            if attachment is not None:
                self.stderr.write(
                    f"Attachment retained for inspection: "
                    f"#{attachment.pk}"
                )

            if container1 is not None:
                self.stderr.write(
                    f"Owner environment retained: "
                    f"#{container1.pk}"
                )

            if container2 is not None:
                self.stderr.write(
                    f"user2 environment retained: "
                    f"#{container2.pk}"
                )

            raise

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Attachment smoke test PASSED"
            )
        )
