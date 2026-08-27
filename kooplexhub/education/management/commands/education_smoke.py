import os
import time
import uuid
import pwd

from django.contrib.auth import get_user_model
from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from education.filesystem import (
    assignment_correct_dir,
    assignment_workdir,
    course_assignment_prepare_root,
)

from education.models import (
    Assignment,
    Course,
    UserAssignmentBinding,
)

from education.services.assignments import (
    collect_assignment_now,
    create_assignment,
    handout_assignment_now,
    submit_assignment,
)

from education.services.lifecycle import (
    CourseCreationService,
)

from education.services.members import (
    add_course_member,
)

from education.services.provisioning import (
    inspect_course_filesystem,
)


User = get_user_model()


class SmokeTimer:
    def __init__(self):
        self.last = time.monotonic()

    def lap(self):
        now = time.monotonic()
        elapsed = now - self.last
        self.last = now
        return elapsed



def wait_for_state(
    *,
    obj,
    field,
    success,
    failure=(),
    timeout=30,
    interval=0.2,
):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        obj.refresh_from_db()

        state = getattr(
            obj,
            field,
        )

        if state in success:
            return obj

        if state in failure:
            error = getattr(
                obj,
                "last_operation_error",
                "",
            )

            raise RuntimeError(
                f"{obj} entered failure state "
                f"{state}: {error}"
            )

        time.sleep(interval)

    obj.refresh_from_db()

    raise TimeoutError(
        f"Timed out waiting for {obj}; "
        f"{field}={getattr(obj, field)}"
    )


def require_posix_user(user):
    try:
        return pwd.getpwnam(
            user.username
        )
    except KeyError as error:
        raise CommandError(
            f'User "{user.username}" is not '
            "available through NSS/getpwnam. "
            "Check LDAP/NSS/SSSD before running "
            "the Education smoke test."
        ) from error


def create_prepare_source(
    *,
    course,
    folder,
    text,
):
    root = course_assignment_prepare_root(
        course
    )

    source = os.path.join(
        root,
        folder,
    )

    os.makedirs(
        source,
        exist_ok=False,
    )

    with open(
        os.path.join(
            source,
            "README.txt",
        ),
        "w",
    ) as handle:
        handle.write(text)

    return source


class Command(BaseCommand):
    help = (
        "Run an end-to-end Education backend "
        "smoke test using real configured services."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--teacher",
            required=True,
        )

        parser.add_argument(
            "--student",
            required=True,
        )

        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
        )

    def step(self, message):
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n>>> {message}"
            )
        )


    def handle(self, *args, **options):
        timeout = options["timeout"]
    
        teacher = User.objects.get(
            username=options["teacher"]
        )
    
        student = User.objects.get(
            username=options["student"]
        )
    
        timer = SmokeTimer()

        self.step("Checking POSIX identities")
        
        require_posix_user(teacher)
        require_posix_user(student)
        
        self.stdout.write(
            self.style.SUCCESS(
                "Teacher and student are available "
                "through NSS"
                f"({timer.lap():.2f}s)"
            )
        )
    
        token = uuid.uuid4().hex[:8]

        self.step("Creating course")
    
        result = CourseCreationService.create(
            owner=teacher,
            name=f"Education smoke {token}",
            description=(
                "Temporary Education integration "
                "smoke-test course."
            ),
            preferred_image=None,
            members=(),
            mounts=(),
            create_environment=False,
        )
    
        course = result.course
    
        course.refresh_from_db()
    
        if (
            course.provisioning_state
            != Course.ProvisioningState.READY
        ):
            raise CommandError(
                "Course did not become READY: "
                f"{course.last_operation_error}"
            )
    
        status = inspect_course_filesystem(
            course=course,
        )
    
        if not status.ready:
            raise CommandError(
                "Course filesystem incomplete: "
                f"{status.missing}"
            )
    
        self.stdout.write(
            self.style.SUCCESS(
                f"Course #{course.pk} READY"
                f"({timer.lap():.2f}s)"
            )
        )


        self.step("Adding student")
        
        student_binding = add_course_member(
            course=course,
            user=student,
            is_teacher=False,
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Student binding #{student_binding.pk}"
                f"({timer.lap():.2f}s)"
            )
        )

        self.step("Creating assignment source folders")
        
        create_prepare_source(
            course=course,
            folder="smoke-submit",
            text=(
                "This assignment will be submitted "
                "by the student.\n"
            ),
        )
        
        create_prepare_source(
            course=course,
            folder="smoke-collect",
            text=(
                "This assignment will be collected "
                "by the teacher.\n"
            ),
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Assignment source folders are created"
                f"({timer.lap():.2f}s)"
            )
        )
    
        self.step("Creating assignment for submission")
        
        submit_assignment_definition = (
            create_assignment(
                course=course,
                actor=teacher,
                folder="smoke-submit",
                name=f"Smoke Submit {token}",
                description=(
                    "Student submission lifecycle test"
                ),
                remove_collected=False,
            )
        )

        wait_for_state(
            obj=submit_assignment_definition,
            field="state",
            success={
                Assignment.State.READY,
            },
            failure={
                Assignment.State.PREPARATION_FAILED,
            },
            timeout=timeout,
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                "Assignment snapshot READY"
                f"({timer.lap():.2f}s)"
            )
        )

        self.step("Handing assignment out")
        
        binding_ids = handout_assignment_now(
            assignment=submit_assignment_definition,
            actor=teacher,
        )
        
        if len(binding_ids) != 1:
            raise CommandError(
                "Expected exactly one student "
                f"handout, got {binding_ids}"
            )
        
        user_assignment = (
            UserAssignmentBinding.objects.get(
                pk=binding_ids[0]
            )
        )
        
        wait_for_state(
            obj=user_assignment,
            field="state",
            success={
                UserAssignmentBinding.State.WORKINPROGRESS,
            },
            failure={
                UserAssignmentBinding.State.HANDOUT_FAILED,
            },
            timeout=timeout,
        )

        workdir = assignment_workdir(
            user_assignment
        )
        
        if not os.path.isfile(
            os.path.join(
                workdir,
                "README.txt",
            )
        ):
            raise CommandError(
                "Handout finished but README.txt "
                "is missing from student workdir."
            )


        self.stdout.write(
            self.style.SUCCESS(
                "Assignment handout complete"
                f"({timer.lap():.2f}s)"
            )
        )
    
        self.step("Simulating student work")
        
        with open(
            os.path.join(
                workdir,
                "answer.txt",
            ),
            "w",
        ) as handle:
            handle.write(
                "Student smoke-test answer.\n"
            )
        
        self.step("Student submits assignment")
        
        submit_assignment(
            binding=user_assignment,
            actor=student,
        )
        
        wait_for_state(
            obj=user_assignment,
            field="state",
            success={
                UserAssignmentBinding.State.COLLECTED,
            },
            failure={
                UserAssignmentBinding.State.COLLECTION_FAILED,
            },
            timeout=timeout,
        )

        correction = assignment_correct_dir(
            user_assignment
        )
        
        if not os.path.isfile(
            os.path.join(
                correction,
                "answer.txt",
            )
        ):
            raise CommandError(
                "Collection completed but student "
                "answer is missing from correction dir."
            )
        
        if user_assignment.submit_count != 1:
            raise CommandError(
                "Student submission did not increment "
                "submit_count."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Assignment submission complete"
                f"({timer.lap():.2f}s)"
            )
        )

        self.step("Creating assignment for collection")

        teacher_collect_assignment = create_assignment(
            course=course,
            actor=teacher,
            folder="smoke-collect",
            name=f"Smoke Collect {token}",
            description=(
                "Teacher collection lifecycle test"
            ),
            remove_collected=False,
        )
        
        wait_for_state(
            obj=teacher_collect_assignment,
            field="state",
            success={Assignment.State.READY},
            failure={
                Assignment.State.PREPARATION_FAILED
            },
            timeout=timeout,
        )

        self.step("Handing collection assignment out")
        
        binding_ids = handout_assignment_now(
            assignment=teacher_collect_assignment,
            actor=teacher,
        )
        
        if len(binding_ids) != 1:
            raise CommandError(
                "Expected exactly one student "
                f"handout, got {binding_ids}"
            )
        
        teacher_collected_binding = (
            UserAssignmentBinding.objects.get(
                pk=binding_ids[0]
            )
        )
        
        wait_for_state(
            obj=teacher_collected_binding,
            field="state",
            success={
                UserAssignmentBinding.State.WORKINPROGRESS,
            },
            failure={
                UserAssignmentBinding.State.HANDOUT_FAILED,
            },
            timeout=timeout,
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Assignment handout complete"
                f"({timer.lap():.2f}s)"
            )
        )

        self.step(
            "Simulating work before teacher collection"
        )
        
        workdir = assignment_workdir(
            teacher_collected_binding
        )
        
        with open(
            os.path.join(
                workdir,
                "teacher-collected-answer.txt",
            ),
            "w",
        ) as handle:
            handle.write(
                "Work collected by the teacher.\n"
            )        

        self.step("Teacher collects assignment")
        
        binding_ids = collect_assignment_now(
            assignment=teacher_collect_assignment,
            actor=teacher,
        )

        if len(binding_ids) != 1:
            raise CommandError(
                "Expected exactly one student "
                f"collection, got {binding_ids}"
            )
        
        teacher_collected_binding = (
            UserAssignmentBinding.objects.get(
                pk=binding_ids[0]
            )
        )

        wait_for_state(
            obj=teacher_collected_binding,
            field="state",
            success={
                UserAssignmentBinding.State.COLLECTED,
            },
            failure={
                UserAssignmentBinding.State.COLLECTION_FAILED,
            },
            timeout=timeout,
        )
        
        teacher_collected_binding.refresh_from_db()
        
        if teacher_collected_binding.submit_count != 0:
            raise CommandError(
                "Teacher collection incorrectly "
                "incremented submit_count."
            )

        correction_dir = assignment_correct_dir(
            teacher_collected_binding
        )
        
        if not os.path.isfile(
            os.path.join(
                correction_dir,
                "teacher-collected-answer.txt",
            )
        ):
            raise CommandError(
                "Teacher collection completed but "
                "the student's modified file is "
                "missing from the correction directory."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Assignment collection complete"
                f"({timer.lap():.2f}s)"
            )
        )

