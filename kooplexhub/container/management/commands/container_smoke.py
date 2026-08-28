import time
import uuid

from django.contrib.auth import get_user_model
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from container.models import (
    Container,
    Image,
)
from container.services.lifecycle import (
    create_container,
    delete_container,
)
from container.services.image_catalog import (
    ImageCatalogService,
)
from container.services.runtime_control import (
    request_start,
    request_stop,
)
from container.services.runtime_query import (
    get_container_log,
)
from container.services.kubernetes.labels import (
    workload_labels,
)
from container.services.kubernetes.wiring import (
    build_pod_operations,
)


User = get_user_model()


def wait_for_state(
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
                f"Environment {container.pk} "
                f"entered failure state "
                f"{container.state}: "
                f"{container.state_backend or ''}"
            )

        time.sleep(interval)

    raise CommandError(
        f"Timed out waiting for environment "
        f"{container.pk}; current state="
        f"{container.state}, "
        f"backend={container.state_backend!r}"
    )


class Command(BaseCommand):
    help = (
        "Run a real Container/Kubernetes "
        "lifecycle smoke test."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            required=True,
            help="Existing Kooplex username.",
        )

        parser.add_argument(
            "--image",
            default=None,
            help=(
                "Project image ID or exact name. "
                "Defaults to the first available "
                "project image."
            ),
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
            return User.objects.get(
                username=username
            )
        except User.DoesNotExist as error:
            raise CommandError(
                f"User {username!r} does not exist."
            ) from error

    def resolve_image(self, user, value):
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
                "No matching available project "
                "image was found."
            )

        return image

    def handle(self, *args, **options):
        timeout = options["timeout"]

        user = self.resolve_user(
            options["user"]
        )

        image = self.resolve_image(
            user,
            options["image"],
        )

        token = uuid.uuid4().hex[:8]
        name = f"smoke-{token}"

        self.step("Creating environment")

        container = create_container(
            user=user,
            image=image,
            name=name,
        )

        self.stdout.write(
            f"Environment #{container.pk}: "
            f"{container.name}"
        )

        self.stdout.write(
            f"Image: {image.name}"
        )

        self.stdout.write(
            f"Initial state: "
            f"{container.get_state_display()}"
        )

        try:
            self.step("Starting environment")

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
                    "Start request did not put "
                    "environment into STARTING."
                )

            if not container.require_running:
                raise CommandError(
                    "Start request did not set "
                    "require_running=True."
                )

            wait_for_state(
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
                    f"Environment RUNNING "
                    f"on {container.runtime_node}"
                )
            )

            self.step(
                "Checking Kubernetes pod"
            )

            pod_operations = (
                build_pod_operations()
            )

            pod = pod_operations.current_pod(
                workload_labels(container)
            )

            if pod is None:
                raise CommandError(
                    "Database says RUNNING but "
                    "no Kubernetes pod exists."
                )

            self.stdout.write(
                f"Pod: {pod.metadata.name}"
            )

            self.stdout.write(
                f"Phase: {pod.status.phase}"
            )

            self.step(
                "Retrieving environment logs"
            )

            logs = get_container_log(
                container
            )

            if logs:
                # Avoid dumping megabytes into a
                # smoke-test terminal.
                self.stdout.write(
                    logs[-4000:]
                )
            else:
                self.stdout.write(
                    "(no log output)"
                )

            self.step(
                "Executing inside environment"
            )

            output = (
                pod_operations
                .exec_for_container(
                    container,
                    (
                        "echo '=== id ==='; "
                        "id; "
                        "echo; "
                        "echo '=== processes ==='; "
                        "ps axu"
                    ),
                )
            )

            self.stdout.write(output)

            # Very useful invariant: exec_for_container
            # explicitly uses `su username`, so make sure
            # we really executed as the requested user.
            if (
                f"({user.username})"
                not in output
                and
                f"uid={user.profile.userid}"
                not in output
                if hasattr(
                    user,
                    "profile",
                )
                else False
            ):
                self.stdout.write(
                    self.style.WARNING(
                        "Could not automatically "
                        "verify UID from exec output."
                    )
                )

            self.step("Stopping environment")

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
                    "Stop request did not put "
                    "environment into STOPPING."
                )

            if container.require_running:
                raise CommandError(
                    "Stop request did not set "
                    "require_running=False."
                )

            wait_for_state(
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
                "Checking pod removal"
            )

            pod = (
                pod_operations.current_pod(
                    workload_labels(container)
                )
            )

            if pod is not None:
                raise CommandError(
                    f"Environment is NOTPRESENT "
                    f"in DB but pod "
                    f"{pod.metadata.name} "
                    f"still exists."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    "Kubernetes pod removed"
                )
            )

        except Exception:
            if container is not None:
                self.stderr.write(
                    self.style.ERROR(
                        "\nSmoke test failed. "
                        f"Environment #{container.pk} "
                        "has deliberately NOT been "
                        "deleted from the database "
                        "so it can be inspected."
                    )
                )

            raise

        self.step(
            "Removing smoke environment"
        )

        container_id = delete_container(
            container=container,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Removed environment "
                f"#{container_id}"
            )
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Container smoke test PASSED"
            )
        )
