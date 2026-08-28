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

from container.models import (
    Container,
)
from container.services.image_catalog import (
    ImageCatalogService,
)
from container.services.kubernetes.wiring import (
    build_pod_operations,
)
from container.services.lifecycle import (
    create_container,
    delete_container,
)
from container.services.runtime_control import (
    request_start,
    request_stop,
)

from project.filesystem import (
    project_container_mountpoint,
    project_workdir,
)
from project.models import (
    Project,
    UserProjectBinding,
)
from project.services.lifecycle import (
    ProjectCreationService,
    delete_project,
)
from project.services.members import (
    MemberSelection,
)
from project.services.provisioning import (
    inspect_project_filesystem,
)


User = get_user_model()


def wait_for_container_states(
    containers,
    *,
    success,
    failure=(),
    timeout=180,
    interval=0.5,
):
    pending = {
        container.pk: container
        for container in containers
    }

    deadline = (
        time.monotonic()
        + timeout
    )

    while pending:
        if time.monotonic() >= deadline:
            states = {
                pk: container.state
                for pk, container
                in pending.items()
            }

            raise CommandError(
                "Timed out waiting for "
                f"environments: {states}"
            )

        for pk, container in list(
            pending.items()
        ):
            container.refresh_from_db()

            if container.state in failure:
                raise CommandError(
                    f"Environment #{pk} entered "
                    f"failure state "
                    f"{container.state}: "
                    f"{container.state_backend!r}"
                )

            if container.state in success:
                pending.pop(pk)

        if pending:
            time.sleep(interval)

    return containers


class Command(BaseCommand):
    help = (
        "Run a real Project + shared "
        "environment integration smoke test."
    )

    def add_arguments(
        self,
        parser,
    ):
        parser.add_argument(
            "--user",
            required=True,
            help=(
                "Existing project creator "
                "username."
            ),
        )

        parser.add_argument(
            "--collaborator",
            default=None,
            help=(
                "Optional existing collaborator "
                "username."
            ),
        )

        parser.add_argument(
            "--image",
            default=None,
            help=(
                "Project image ID or exact name. "
                "Defaults to the first available "
                "Project image."
            ),
        )

        parser.add_argument(
            "--timeout",
            type=int,
            default=180,
        )

    def step(
        self,
        text,
    ):
        self.stdout.write("")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f">>> {text}"
            )
        )

    def resolve_user(
        self,
        username,
    ):
        try:
            return User.objects.get(
                username=username
            )

        except User.DoesNotExist as error:
            raise CommandError(
                f"User {username!r} "
                "does not exist."
            ) from error

    def resolve_image(
        self,
        value,
    ):
        images = (
            ImageCatalogService
            .available_for_user(
                self.owner
            )
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
                "No matching Project image "
                "was found."
            )

        return image

    def handle(
        self,
        *args,
        **options,
    ):
        timeout = options["timeout"]

        self.owner = self.resolve_user(
            options["user"]
        )

        collaborator = None

        if options["collaborator"]:
            collaborator = (
                self.resolve_user(
                    options["collaborator"]
                )
            )

            if (
                collaborator.pk
                == self.owner.pk
            ):
                raise CommandError(
                    "Creator and collaborator "
                    "must be different users."
                )

        image = self.resolve_image(
            options["image"]
        )

        token = uuid.uuid4().hex[:8]

        project_name = (
            f"Smoke project {token}"
        )

        owner_container = None
        collaborator_container = None
        project = None

        members = ()

        if collaborator is not None:
            members = (
                MemberSelection(
                    user=collaborator,
                    role=(
                        UserProjectBinding
                        .Role
                        .COLLABORATOR
                    ),
                ),
            )

        self.step("Creating project")

        try:
            result = (
                ProjectCreationService
                .create(
                    owner=self.owner,
                    name=project_name,
                    scope=(
                        Project.Scope.PRIVATE
                    ),
                    description=(
                        "Automated Project "
                        "lifecycle smoke test."
                    ),
                    preferred_image=image,
                    members=members,
                    mounts=(),
                    create_environment=False,
                )
            )

            project = result.project

            project.refresh_from_db()

            if (
                project.provisioning_state
                !=
                Project.ProvisioningState.READY
            ):
                raise CommandError(
                    "Project was created but "
                    "did not become READY: "
                    f"{project.provisioning_state}; "
                    f"{project.last_operation_error}"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Project #{project.pk} READY"
                )
            )

            status = (
                inspect_project_filesystem(
                    project=project
                )
            )

            if not status.ready:
                raise CommandError(
                    "Project filesystem "
                    "incomplete: "
                    f"{status.missing}"
                )

            if collaborator is not None:
                if not (
                    UserProjectBinding.objects
                    .filter(
                        project=project,
                        user=collaborator,
                        role=(
                            UserProjectBinding
                            .Role
                            .COLLABORATOR
                        ),
                    )
                    .exists()
                ):
                    raise CommandError(
                        "Collaborator binding "
                        "was not created."
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        "Collaborator added"
                    )
                )

            self.step(
                "Writing shared project material"
            )

            marker_name = (
                f"smoke-{token}.txt"
            )

            marker_content = (
                f"project-smoke:{token}"
            )

            marker_path = os.path.join(
                project_workdir(project),
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

            if not os.path.isfile(
                marker_path
            ):
                raise CommandError(
                    "Smoke marker was not "
                    "created in project workdir."
                )

            self.stdout.write(
                f"Marker: {marker_path}"
            )

            self.step(
                "Creating owner environment"
            )

            owner_container = (
                create_container(
                    user=self.owner,
                    name=(
                        f"project-smoke-"
                        f"{token}-owner"
                    ),
                    image=image,
                    project_ids=(
                        project.pk,
                    ),
                )
            )

            self.stdout.write(
                f"Owner environment "
                f"#{owner_container.pk}"
            )

            containers = [
                (
                    owner_container,
                    self.owner,
                )
            ]

            if collaborator is not None:
                self.step(
                    "Creating collaborator "
                    "environment"
                )

                collaborator_container = (
                    create_container(
                        user=collaborator,
                        name=(
                            f"project-smoke-"
                            f"{token}-collaborator"
                        ),
                        image=image,
                        project_ids=(
                            project.pk,
                        ),
                    )
                )

                containers.append(
                    (
                        collaborator_container,
                        collaborator,
                    )
                )

                self.stdout.write(
                    f"Collaborator environment "
                    f"#{collaborator_container.pk}"
                )

            self.step(
                "Starting environment(s)"
            )

            # Queue all starts before waiting.
            # If the container Huey queue has
            # multiple workers, these really do
            # proceed concurrently.
            for container, user in containers:
                request_start(
                    container=container,
                    actor=user,
                )

            wait_for_container_states(
                [
                    container
                    for container, _user
                    in containers
                ],
                success={
                    Container.State.RUNNING,
                    Container.State.NEED_RESTART,
                },
                failure={
                    Container.State.ERROR,
                },
                timeout=timeout,
            )

            for container, _user in containers:
                container.refresh_from_db()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Environment "
                        f"#{container.pk} "
                        f"RUNNING on "
                        f"{container.runtime_node}"
                    )
                )

            self.step(
                "Checking shared project mount"
            )

            pod_operations = (
                build_pod_operations()
            )

            mountpoint = (
                project_container_mountpoint(
                    project
                )
            )

            mounted_marker = os.path.join(
                mountpoint,
                marker_name,
            )

            quoted_marker = shlex.quote(
                mounted_marker
            )

            for container, user in containers:
                output = (
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
                )

                if (
                    output.strip()
                    != marker_content
                ):
                    raise CommandError(
                        f"Environment "
                        f"#{container.pk} "
                        f"({user.username}) "
                        "cannot see the expected "
                        "project marker. "
                        f"Output={output!r}"
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{user.username}: "
                        "shared file visible"
                    )
                )

            self.step(
                "Stopping environment(s)"
            )

            # Queue all stops first as well.
            for container, user in containers:
                request_stop(
                    container=container,
                    actor=user,
                )

            wait_for_container_states(
                [
                    container
                    for container, _user
                    in containers
                ],
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
                    "All environments "
                    "NOTPRESENT"
                )
            )

            self.step(
                "Deleting environment(s)"
            )

            for container, _user in containers:
                container.refresh_from_db()

                deleted_id = (
                    delete_container(
                        container=container,
                    )
                )

                self.stdout.write(
                    f"Deleted environment "
                    f"#{deleted_id}"
                )

            # Important: this also proves the
            # ProjectContainerBindings disappeared.
            if project.containerbindings.exists():
                raise CommandError(
                    "Project still has container "
                    "bindings after environment "
                    "deletion."
                )

            self.step("Deleting project")

            project_id = project.pk

            delete_project(
                project=project,
                actor=self.owner,
                archive=False,
            )

            if Project.objects.filter(
                pk=project_id
            ).exists():
                raise CommandError(
                    "Project row still exists "
                    "after deletion."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Deleted project "
                    f"#{project_id}"
                )
            )

        except Exception:
            self.stderr.write(
                self.style.ERROR(
                    "\nProject smoke test "
                    "FAILED."
                )
            )

            if project is not None:
                self.stderr.write(
                    f"Project #{project.pk}"
                )

            if owner_container is not None:
                self.stderr.write(
                    f"Owner environment "
                    f"#{owner_container.pk}"
                )

            if (
                collaborator_container
                is not None
            ):
                self.stderr.write(
                    "Collaborator environment "
                    f"#{collaborator_container.pk}"
                )

            self.stderr.write(
                "Resources were deliberately "
                "left in place for inspection."
            )

            raise

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Project smoke test PASSED"
            )
        )
