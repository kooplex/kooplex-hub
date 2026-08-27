from django.db import models
from django.contrib.auth import get_user_model

from kooplexhub.lib.libbase import standardize_str
from . import Course


User = get_user_model()

class AssignmentQuerySet(models.QuerySet):

    def for_course(self, course):
        return self.filter(course=course)

    def visible_to(self, user):
        if not user.is_authenticated:
            return self.none()

        return self.filter(
            course__userbindings__user=user,
        ).distinct()

    def manageable_by(self, user):
        if not user.is_authenticated:
            return self.none()

        return self.filter(
            course__userbindings__user=user,
            course__userbindings__is_teacher=True,
        ).distinct()


class Assignment(models.Model):
    class State(models.TextChoices):
        PREPARING = "prp", "Preparing"
        READY = "rdy", "Ready"
        PREPARATION_FAILED = "pfl", "Preparation failed"
    
    name = models.CharField(max_length = 32, null = False)
    course = models.ForeignKey(
        Course, 
        null=False, 
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    creator = models.ForeignKey(
        User, 
        null=False, 
        on_delete=models.CASCADE,
        related_name="created_assignments",
    )

    description = models.TextField(max_length = 500)
    folder = models.CharField(max_length = 32, null = False)
    created_at = models.DateTimeField(editable=False,null=True,auto_now_add=True)
    valid_from = models.DateTimeField(blank=True,null=True)
    expires_at = models.DateTimeField(blank=True,null=True)
    remove_collected = models.BooleanField(default = False,null=True)
    max_size = models.IntegerField(default = None, null = True, blank = True) 
    filename = models.CharField(max_length = 256, null = False, unique = True)
    handout_when_ready = models.BooleanField(
        default=False,
    )
    state = models.CharField(
        max_length=16,
        choices=State.choices,
        default=State.PREPARING,
    )
    last_operation_error = models.TextField(
        blank=True,
        default="",
    )
    last_operation_failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    objects = AssignmentQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "folder"],
                name="unique_assignment_folder_per_course",
            ),
            models.UniqueConstraint(
                fields=["course", "name"],
                name="unique_assignment_name_per_course",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(valid_from__isnull=True)
                    | models.Q(expires_at__isnull=True)
                    | models.Q(valid_from__lt=models.F("expires_at"))
                ),
                name="assignment_valid_time_window",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(max_size__isnull=True)
                    | models.Q(max_size__gt=0)
                ),
                name="assignment_positive_max_size",
            ),
        ]

    def __str__(self):
        return f"Assignment {self.name} (course {self.course.name}@{self.creator.username})"

    @property
    def _safename(self):
        return standardize_str(f'{self.course.name}-{self.folder}')


class UserAssignmentBinding(models.Model):
    class State(models.TextChoices):
        QUEUED = "qed", "Waiting for handout"
        EXTRACTING = "ext", "Handout in progress"
        WORKINPROGRESS = "wip", "Working on assignment"
        COMPRESSING = "snap", "Collection in progress"
        COLLECTED = "col", "Collected, waiting for correction"
        READY = "rdy", "Corrected"

        HANDOUT_FAILED = "hfl", "Handout failed"
        COLLECTION_FAILED = "cfl", "Collection failed"

    user = models.ForeignKey(
        User, 
        null=False, 
        on_delete=models.CASCADE,
        related_name="assignmentbindings",
    )
    assignment = models.ForeignKey(
        Assignment, 
        null=False, 
        on_delete=models.CASCADE,
        related_name="userbindings",
    )
    state = models.CharField(
        max_length=16, 
        choices=State.choices, 
        default=State.QUEUED,
    )
    corrector = models.ForeignKey(
        User, 
        null=True, 
        blank=True,
        related_name="corrected_assignmentbindings", 
        on_delete=models.SET_NULL, 
    )
    last_received_at = models.DateTimeField(editable=False,null=True)
    last_submitted_at = models.DateTimeField(editable=False,null=True)
    last_corrected_at = models.DateTimeField(editable=False,null=True)
    last_operation_error = models.TextField(
        blank=True,
        default="",
    )
    
    last_operation_failed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    score = models.FloatField(null = True, default = None, blank = True)
    feedback_text = models.TextField(null = True, default = None, blank = True)
    submit_count = models.IntegerField(default = 0, null = False)
    correction_count = models.IntegerField(default = 0, null = False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "assignment"],
                name="unique_user_assignment_binding",
            ),
        ]
        ordering = [ 'assignment__name' ]
        indexes = [
            models.Index(
                fields=["assignment", "state"],
                name="uab_assignment_state_idx",
            ),
            models.Index(
                fields=["user", "state"],
                name="uab_user_state_idx",
            ),
        ]


    def __str__(self):
        return f'{self.assignment.name} ({self.assignment.course.name})'


