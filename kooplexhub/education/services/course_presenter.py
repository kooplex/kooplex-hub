from django.db.models.functions import Lower
from django.urls import reverse

from ..models import (
    Assignment, 
    UserAssignmentBinding,
)
from ..services.assignment_presenter import AssignmentPresenter


class CoursePresenter:

    def __init__(self, binding, user):
        self.binding = binding
        self.course = binding.course
        self.user = user

    @property
    def card_dom_id(self):
        return f"course-card-{self.course.pk}"

    @property
    def role(self):
        return self.binding.role

    @property
    def is_teacher(self):
        return self.binding.is_teacher

    @property
    def is_student(self):
        return self.binding.is_student

    @property
    def can_edit(self):
        return self.binding.is_teacher

    @property
    def can_edit_name(self):
        return self.can_edit

    @property
    def can_edit_description(self):
        return self.can_edit

    @property
    def can_manage_members(self):
        return self.can_edit

    @property
    def can_manage_assignments(self):
        return self.can_edit

    @property
    def can_submit_assignments(self):
        return self.is_student

    @property
    def role_css_class(self):
        return (
            "course-card--teacher"
            if self.is_teacher
            else "course-card--student"
        )

    @property
    def role_label(self):
        return "Teacher" if self.is_teacher else "Student"

    @property
    def assignments_dom_id(self):
        return f"course-assignments-{self.course.pk}"

    @property
    def assignments_url(self):
        return reverse(
            "education:course-assignments",
            kwargs={"course_id": self.course.pk},
        )

    def get_assignments(self):
    
        if self.is_teacher:
            assignments = (
                Assignment.objects
                .filter(course=self.course)
                .select_related("creator")
                .order_by(Lower("name"))
            )
    
            return [
                AssignmentPresenter(
                    assignment=assignment,
                    course_presenter=self,
                )
                for assignment in assignments
            ]
    
        bindings = (
            UserAssignmentBinding.objects
            .filter(
                user=self.user,
                assignment__course=self.course,
            )
            .select_related(
                "assignment",
                "assignment__creator",
                "corrector",
            )
            .order_by(Lower("assignment__name"))
        )
    
        return [
            AssignmentPresenter(
                assignment=binding.assignment,
                course_presenter=self,
                user_binding=binding,
            )
            for binding in bindings
        ]

