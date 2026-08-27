from functools import cached_property

from django.db.models.functions import Lower
from django.urls import reverse

from ..models import (
    Assignment, 
    UserAssignmentBinding,
)
from ..services.assignment_presenter import AssignmentPresenter
from ..filesystem import get_assignment_prepare_subfolders


class CoursePresenter:

    def __init__(self, binding):
        self.binding = binding
        self.course = binding.course

    @property
    def user(self):
        return self.binding.user

    @property
    def is_teacher(self):
        return self.binding.is_teacher

    @property
    def is_student(self):
        return self.binding.is_student

    @property
    def can_edit(self):
        return self.is_teacher

    @property
    def can_edit_name(self):
        return self.is_teacher

    @property
    def can_edit_description(self):
        return self.is_teacher

    @property
    def can_manage_members(self):
        return self.is_teacher

    @property
    def can_change_image(self):
        return self.is_teacher
    
    @property
    def can_change_mounts(self):
        return self.is_teacher
    
    @property
    def can_create_environment(self):
        return True


    @property
    def can_create_assignment(self):
        return (
            self.is_teacher
            and bool(self.available_assignment_sources)
        )

    @property
    def can_manage_assignments(self):
        return self.is_teacher

    @property
    def can_submit_assignments(self):
        return self.is_student


    @cached_property
    def environment_containers(self):
        bindings = self.course.containerbindings.all()
    
        containers = [
            binding.container
            for binding in bindings
            if binding.container.user_id == self.user.id
        ]
    
        return sorted(
            containers,
            key=lambda container: container.name.lower(),
        )
    
    
    @property
    def has_environment_containers(self):
        return bool(self.environment_containers)
    
    
    @property
    def can_generate_default_environment(self):
        return (
            self.can_create_environment
            and self.course.preferred_image_id is not None
            and not self.has_environment_containers
        )
    
    
    @property
    def default_environment_disabled_reason(self):
        if not self.can_create_environment:
            return "You do not have permission to create an environment."
    
        if self.course.preferred_image_id is None:
            return "Select a preferred image first."
    
        if self.has_environment_containers:
            return "An environment already exists."
    
        return None
    
    
    @property
    def preferred_image_label(self):
        if self.course.preferred_image:
            return self.course.preferred_image.short_name
    
        return "No preferred image"


    @cached_property
    def available_assignment_sources(self):
        if not self.is_teacher:
            return ()
    
        return tuple(
            get_assignment_prepare_subfolders(
                self.course
            )
        )
    
    @property
    def can_create_assignment(self):
        return (
            self.is_teacher
            and bool(self.available_assignment_sources)
        )
    
    @property
    def assignment_create_disabled_reason(self):
        if not self.is_teacher:
            return "Only teachers can create assignments."
    
        if not self.available_assignment_sources:
            return (
                "Put assignment material into a new "
                "folder in the preparation directory first."
            )
    
        return None
    
    @property
    def assignment_create_url(self):
        return reverse(
            "education:assignment-create-modal",
            kwargs={
                "course_id": self.course.pk,
            },
        )

    @property
    def card_dom_id(self):
        return f"course-card-{self.course.pk}"

    @property
    def description_pane_id(self):
        return f"course-description-pane-{self.course.pk}"
    
    @property
    def assignments_pane_id(self):
        return f"course-assignments-pane-{self.course.pk}"

    @property
    def assignments_list_dom_id(self):
        return f"course-assignments-list-{self.course.pk}"
    
    @property
    def people_pane_id(self):
        return f"course-people-pane-{self.course.pk}"
    
    @property
    def environment_pane_id(self):
        return f"course-environment-pane-{self.course.pk}"
    
    @property
    def environment_content_dom_id(self):
        return f"course-environment-content-{self.course.pk}"


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

    @property
    def assignment_attention_count(self):
        if not self.is_student:
            return 0

        return sum(
            1
            for assignment_ui in self.get_assignments()
            if assignment_ui.can_submit
        )
    
    @property
    def has_assignment_attention(self):
        return self.assignment_attention_count > 0
