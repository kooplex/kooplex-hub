from functools import cached_property

from django.urls import reverse

from .assignments import (
    count_handout_candidates,
    count_collect_candidates,
)
from ..filesystem import get_assignment_prepare_subfolders
from ..models import (
    UserAssignmentBinding,
)

class AssignmentPresenter:

    def __init__(
        self, 
        assignment, 
        course_presenter,
        user_binding=None,
    ):
        self.assignment = assignment
        self.course_ui = course_presenter
        self.user_binding = user_binding


    @property
    def is_teacher(self):
        return self.course_ui.is_teacher
    
    @property
    def is_student(self):
        return self.course_ui.is_student


    @property
    def can_edit(self):
        return self.course_ui.is_teacher

    @property
    def can_delete(self):
        if not self.course_ui.is_teacher:
            return False

        if self.assignment.creator_id == self.course_ui.user.id:
            return True

        return (
            self.assignment.course
            .teacher_can_delete_foreign_assignment
        )

    @property
    def can_score(self):
        return self.course_ui.is_teacher

    @property
    def can_submit(self):
        return (
            self.is_student
            and self.user_binding is not None
            and self.user_binding.state
            == UserAssignmentBinding.State.WORKINPROGRESS
        )


    @property
    def state(self):
        if self.user_binding is None:
            return None
    
        return self.user_binding.state

    @property
    def state_label(self):
        if self.user_binding is None:
            return "—"
    
        return self.user_binding.get_state_display()


    @property
    def score(self):
        if self.user_binding is None:
            return None
    
        return self.user_binding.score
    
    @property
    def feedback(self):
        if self.user_binding is None:
            return None
    
        return self.user_binding.feedback_text


    @property
    def received_at(self):
        return (
            self.user_binding.last_received_at
            if self.user_binding
            else None
        )
    
    @property
    def submitted_at(self):
        return (
            self.user_binding.last_submitted_at
            if self.user_binding
            else None
        )
    
    @property
    def corrected_at(self):
        return (
            self.user_binding.last_corrected_at
            if self.user_binding
            else None
        )


    @property
    def handout_candidate_count(self):
        if not self.is_teacher:
            return 0
    
        return count_handout_candidates(
            self.assignment
        )
    
    @property
    def collect_candidate_count(self):
        if not self.is_teacher:
            return 0
    
        return count_collect_candidates(
            self.assignment
        )


    @cached_property
    def available_assignment_sources(self):
        return get_assignment_prepare_subfolders(
            self.course
        )
    
    
    @property
    def can_create_assignment(self):
        return (
            self.is_teacher
            and bool(
                self.available_assignment_sources
            )
        )


    @property
    def handout_at(self):
        if self.user_binding is None:
            return None
        return self.user_binding.last_received_at
    
    
    @property
    def collected_at(self):
        if self.user_binding is None:
            return None
        return self.user_binding.last_submitted_at
    
    
    @property
    def corrected_at(self):
        if self.user_binding is None:
            return None
        return self.user_binding.last_corrected_at


    @property
    def schedule_url(self):
        return reverse(
            "education:assignment-schedule",
            kwargs={
                "course_id": self.assignment.course_id,
                "assignment_id": self.assignment.pk,
            },
        )
    
    @property
    def handout_now_url(self):
        return reverse(
            "education:assignment-handout-now",
            kwargs={
                "course_id": self.assignment.course_id,
                "assignment_id": self.assignment.pk,
            },
        )
    
    @property
    def collect_now_url(self):
        return reverse(
            "education:assignment-collect-now",
            kwargs={
                "course_id": self.assignment.course_id,
                "assignment_id": self.assignment.pk,
            },
        )
    
    @property
    def submit_url(self):
        return reverse(
            "education:assignment-submit",
            kwargs={
                "course_id": self.assignment.course_id,
                "assignment_id": self.assignment.pk,
            },
        )

