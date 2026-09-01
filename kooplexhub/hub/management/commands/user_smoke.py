import os
import shlex
import time
import uuid

from django.contrib.auth import (
    get_user_model,
)
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from container.models import Container
from container.services.image_catalog import (
    ImageCatalogService,
)
from container.services.kubernetes.labels import (
    workload_labels,
)
from container.services.kubernetes.wiring import (
    build_pod_operations,
)
from container.services.lifecycle import (
    create_container,
)
from container.services.runtime_control import (
    request_start,
    request_stop,
)

from hub.conf import HUB_SETTINGS
from hub.filesystem import (
    user_home,
    user_garbage,
    user_scratch,
)
from hub.lib.ldap import Ldap
from hub.models import Profile
from hub.services.kubernetes_identity import (
    inspect_user_kubernetes_identity,
)
from hub.services.user_lifecycle import (
    create_user,
)


User = get_user_model()


def wait_for_profile(
    profile,
    *,
    timeout,
    interval=0.5,
):
    deadline = (
        time.monotonic()
        + timeout
    )

    while time.monotonic() < deadline:
        profile.refresh_from_db()

        if profile.state == Profile.State.READY:
            return profile

        if (
            profile.state
            == Profile.State.PROVISION_FAILED
        ):
            raise CommandError(
                "User provisioning failed: "
                f"{profile.last_operation_error}"
            )

        time.sleep(interval)

    raise CommandError(
        "Timed out waiting for user "
        "provisioning; "
        f"state={profile.state}, "
        f"error="
        f"{profile.last_operation_error!r}"
    )


def wait_for_container(
    container,
    *,
    success,
    failure=(),
    timeout,
    interval=0.5,
):
    deadline = (
        time.monotonic()
        + timeout
    )

    while time.monotonic() < deadline:
        container.refresh_from_db()

        if container.state in success:
            return container

        if container.state in failure:
            raise CommandError(
                f"Environment #{container.pk} "
                "entered failure state "
                f"{container.state}: "
                f"{container.state_backend!r}"
            )

        time.sleep(interval)

    raise CommandError(
        f"Timed out waiting for environment "
        f"#{container.pk}; "
        f"state={container.state}, "
        f"backend="
        f"{container.state_backend!r}"
    )


class Command(BaseCommand):
    help = (
        "Run the real Kooplex user "
        "provisioning lifecycle through a "
        "started and stopped environment."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--username",
            default=None,
            help=(
                "Smoke username. If omitted, "
                "a unique username is generated."
            ),
        )

        parser.add_argument(
            "--image",
            default=None,
            help=(
                "Project image ID or exact "
                "name. Defaults to first "
                "available Project image."
            ),
        )

        parser.add_argument(
            "--timeout",
            type=int,
            default=180,
        )

    def step(
        self,
        message,
    ):
        self.stdout.write("")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f">>> {message}"
            )
        )

    def resolve_image(
        self,
        *,
        user,
        value,
    ):
        images = (
            ImageCatalogService
            .available_for_user(user)
        )

        if value is None:
            image = images.first()

        elif str(value).isdigit():
            image = images.filter(
                pk=int(value)
            ).first()

        else:
            image = images.filter(
                name=value
            ).first()

        if image is None:
            raise CommandError(
                "No matching available "
                "Project image was found."
            )

        if not image.require_home:
            raise CommandError(
                "The selected image does not "
                "mount the user home directory."
            )

        return image

    def handle(
        self,
        *args,
        **options,
    ):
        timeout = options["timeout"]

        token = uuid.uuid4().hex[:8]

        username = (
            options["username"]
            or f"smoke-user-{token}"
        )

        if User.objects.filter(
            username=username
        ).exists():
            raise CommandError(
                f"User {username!r} already "
                "exists."
            )

        user = None
        container = None

        self.step("Creating user")

        try:
            user = create_user(
                username=username,
                email=(
                    f"{username}@smoke.invalid"
                ),
                first_name="Smoke",
                last_name="User",
            )

            self.stdout.write(
                f"User #{user.pk}: "
                f"{user.username}"
            )

            profile = (
                Profile.objects.get(
                    user=user
                )
            )

            self.stdout.write(
                "Initial Profile state: "
                f"{profile.get_state_display()}"
            )

            self.step(
                "Waiting for user provisioning"
            )

            wait_for_profile(
                profile,
                timeout=timeout,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Profile READY"
                )
            )

            self.stdout.write(
                f"UID: {profile.uid_number}"
            )

            self.stdout.write(
                f"GID: {profile.gid_number}"
            )

            if profile.uid_number is None:
                raise CommandError(
                    "Profile READY but UID "
                    "is missing."
                )

            if profile.gid_number is None:
                raise CommandError(
                    "Profile READY but GID "
                    "is missing."
                )

            if not profile.token:
                raise CommandError(
                    "Profile READY but job "
                    "token is missing."
                )

            self.step(
                "Checking LDAP identity"
            )

            ldap_entry = (
                Ldap().get_user(user)
            )

            ldap_uid = int(
                ldap_entry.uidNumber.value
            )

            ldap_gid = int(
                ldap_entry.gidNumber.value
            )

            if (
                ldap_uid
                != profile.uid_number
            ):
                raise CommandError(
                    "LDAP/Profile UID mismatch: "
                    f"{ldap_uid} != "
                    f"{profile.uid_number}"
                )

            if (
                ldap_gid
                != profile.gid_number
            ):
                raise CommandError(
                    "LDAP/Profile GID mismatch: "
                    f"{ldap_gid} != "
                    f"{profile.gid_number}"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "LDAP identity matches "
                    "Profile"
                )
            )

            self.step(
                "Checking provisioned storage"
            )

            home = user_home(user)

            if not os.path.isdir(home):
                raise CommandError(
                    f"Home directory missing: "
                    f"{home}"
                )

            self.stdout.write(
                f"Home: {home}"
            )

            garbage = user_garbage(user)

            if garbage is not None:
                if not os.path.isdir(
                    garbage
                ):
                    raise CommandError(
                        "Configured garbage "
                        "directory missing: "
                        f"{garbage}"
                    )

                self.stdout.write(
                    f"Garbage: {garbage}"
                )

            scratch = user_scratch(user)

            if (
                profile.has_scratch
                and scratch is not None
            ):
                if not os.path.isdir(
                    scratch
                ):
                    raise CommandError(
                        "Configured scratch "
                        "directory missing: "
                        f"{scratch}"
                    )

                self.stdout.write(
                    f"Scratch: {scratch}"
                )

            self.step(
                "Checking Kubernetes identity"
            )

            identity_status = (
                inspect_user_kubernetes_identity(
                    profile=profile
                )
            )

            if (
                HUB_SETTINGS
                .kubernetes_identity
                .enabled
                and not identity_status
            ):
                raise CommandError(
                    "Kubernetes identity is "
                    "enabled but no namespaces "
                    "were inspected."
                )

            for status in identity_status:
                self.stdout.write(
                    f"{status.namespace}: "
                    f"present="
                    f"{status.secret_present}, "
                    f"token="
                    f"{status.token_matches}"
                )

                if not status.ready:
                    raise CommandError(
                        "Kubernetes identity "
                        "incomplete in namespace "
                        f"{status.namespace}"
                    )

            self.step(
                "Writing README into home"
            )

            marker_name = (
                "README-kooplex-smoke.txt"
            )

            marker_content = (
                "Kooplex user lifecycle "
                f"smoke {token}"
            )

            marker_path = os.path.join(
                home,
                marker_name,
            )

            with open(
                marker_path,
                "w",
                encoding="utf-8",
            ) as handle:
                handle.write(
                    marker_content + "\n"
                )

            with open(
                marker_path,
                "r",
                encoding="utf-8",
            ) as handle:
                observed = (
                    handle.read().strip()
                )

            if observed != marker_content:
                raise CommandError(
                    "Home README content "
                    "does not match."
                )

            self.stdout.write(
                f"Created: {marker_path}"
            )

            self.step(
                "Selecting Project image"
            )

            image = self.resolve_image(
                user=user,
                value=options["image"],
            )

            self.stdout.write(
                f"Image: {image.name}"
            )

            self.step(
                "Creating environment"
            )

            container = create_container(
                user=user,
                image=image,
                name=(
                    f"user-smoke-{token}"
                ),
            )

            self.stdout.write(
                f"Environment "
                f"#{container.pk}: "
                f"{container.name}"
            )

            self.step(
                "Starting environment"
            )

            request_start(
                container=container,
                actor=user,
            )

            container.refresh_from_db()

            if (
                container.state
                != Container.State.STARTING
            ):
                raise CommandError(
                    "Start request did not "
                    "enter STARTING."
                )

            wait_for_container(
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

            self.stdout.write(
                self.style.SUCCESS(
                    "Environment RUNNING "
                    f"on "
                    f"{container.runtime_node}"
                )
            )

            pod_operations = (
                build_pod_operations()
            )

            pod = (
                pod_operations.current_pod(
                    workload_labels(
                        container
                    )
                )
            )

            if pod is None:
                raise CommandError(
                    "Environment is RUNNING "
                    "but Kubernetes pod is "
                    "missing."
                )

            self.stdout.write(
                f"Pod: {pod.metadata.name}"
            )

            self.step(
                "Checking home mount as root"
            )

            container_home = (
                HUB_SETTINGS
                .mounts
                .home
                .mountpoint
                .format(user=user)
            )

            container_marker = os.path.join(
                container_home,
                marker_name,
            )

            quoted_marker = shlex.quote(
                container_marker
            )

            root_output = (
                pod_operations
                .exec_for_container_root(
                    container,
                    (
                        f"test -f "
                        f"{quoted_marker} "
                        f"&& cat "
                        f"{quoted_marker}"
                    ),
                )
                .strip()
            )

            if root_output != marker_content:
                raise CommandError(
                    "Mounted README differs "
                    "from host README. "
                    f"Output={root_output!r}"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "Home README visible "
                    "inside Container"
                )
            )

            self.step(
                "Checking LDAP/NSS identity "
                "inside environment"
            )

            user_output = (
                pod_operations
                .exec_for_container(
                    container,
                    (
                        "echo '=== identity ==='; "
                        "id; "
                        "echo '=== README ==='; "
                        f"cat {quoted_marker}"
                    ),
                )
            )

            self.stdout.write(
                user_output
            )

            if marker_content not in user_output:
                raise CommandError(
                    "User-level exec cannot "
                    "read the mounted README."
                )

            expected_uid = (
                f"uid={profile.uid_number}"
            )

            if expected_uid not in user_output:
                raise CommandError(
                    "Container does not resolve "
                    "the provisioned UID. "
                    f"Expected {expected_uid!r}."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "Container resolves the "
                    "new user correctly"
                )
            )

            self.step(
                "Stopping environment"
            )

            request_stop(
                container=container,
                actor=user,
            )

            container.refresh_from_db()

            if (
                container.state
                != Container.State.STOPPING
            ):
                raise CommandError(
                    "Stop request did not "
                    "enter STOPPING."
                )

            wait_for_container(
                container,
                success={
                    Container.State.NOTPRESENT,
                },
                failure={
                    Container.State.ERROR,
                },
                timeout=timeout,
            )

            self.stdout.write(
                self.style.SUCCESS(
                    "Environment NOTPRESENT"
                )
            )

            self.step(
                "Checking Kubernetes pod "
                "removal"
            )

            pod = (
                pod_operations.current_pod(
                    workload_labels(
                        container
                    )
                )
            )

            if pod is not None:
                raise CommandError(
                    "Environment is "
                    "NOTPRESENT but pod still "
                    f"exists: "
                    f"{pod.metadata.name}"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "Kubernetes pod removed"
                )
            )

        except Exception:
            self.stderr.write("")
            self.stderr.write(
                self.style.ERROR(
                    "USER SMOKE FAILED"
                )
            )

            if user is not None:
                self.stderr.write(
                    f"User retained for "
                    f"inspection: "
                    f"#{user.pk} "
                    f"{user.username}"
                )

            if container is not None:
                self.stderr.write(
                    f"Environment retained "
                    f"for inspection: "
                    f"#{container.pk}"
                )

            raise

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "USER PROVISIONING SMOKE "
                "PASSED"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                "User and NOTPRESENT "
                "environment were deliberately "
                "retained. User deletion is "
                "not part of this smoke yet."
            )
        )

        self.stdout.write(
            f"User #{user.pk}: "
            f"{user.username}"
        )

        self.stdout.write(
            f"Environment "
            f"#{container.pk}: "
            f"{container.name}"
        )


