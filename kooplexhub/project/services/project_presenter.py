from functools import cached_property
from dataclasses import dataclass

from django.urls import reverse

from ..models import UserProjectBinding


@dataclass
class ProjectPresenter:
    project: object
    user: object

    def __post_init__(self):
        self._binding = self.get_user_binding()

    def get_user_binding(self):
        if not self.user or not self.user.is_authenticated:
            return None

        prefetched = getattr(
            self.project,
            "_prefetched_objects_cache",
            {},
        ).get("userbindings")

        if prefetched is not None:
            return next(
                (
                    binding
                    for binding in prefetched
                    if binding.user_id == self.user.pk
                ),
                None,
            )

        return (
            self.project.userbindings
            .filter(user=self.user)
            .first()
        )

    @cached_property
    def binding(self):
        return self._binding

    @property
    def role(self):
        if self.user.is_superuser:
            return UserProjectBinding.Role.CREATOR

        if not self.binding:
            return None

        return self.binding.role

    @property
    def role_label(self):
        if self.user.is_superuser:
            return "Administrator"

        if not self.binding:
            return "Viewer"

        return self.binding.get_role_display()

    @property
    def is_creator(self):
        return (
            self.user.is_superuser
            or self.role == UserProjectBinding.Role.CREATOR
        )

    @property
    def is_admin(self):
        return self.role == UserProjectBinding.Role.ADMIN

    @property
    def is_collaborator(self):
        return (
            self.role
            == UserProjectBinding.Role.COLLABORATOR
        )

    @property
    def can_edit(self):
        return (
            self.user.is_superuser
            or self.is_creator
            or self.is_admin
        )

    @property
    def can_edit_name(self):
        return self.can_edit

    @property
    def can_edit_description(self):
        return self.can_edit

    @property
    def can_change_scope(self):
        return self.can_edit

    @property
    def can_manage_members(self):
        return self.can_edit

    @property
    def can_change_image(self):
        return self.can_edit

    @property
    def can_change_mounts(self):
        return self.can_edit

    @property
    def can_create_environment(self):
        return self.binding is not None or self.user.is_superuser

    @property
    def can_delete(self):
        return self.is_creator

    @property
    def can_leave(self):
        return (
            self.binding is not None
            and not self.is_creator
        )

    @property
    def membership_action_label(self):
        if self.can_delete:
            return "Delete project"

        if self.can_leave:
            return "Leave project"

        return None

    @property
    def membership_action_icon(self):
        if self.can_delete:
            return "bi bi-trash"

        if self.can_leave:
            return "bi bi-box-arrow-right"

        return None

    @property
    def membership_action_url(self):
        return reverse(
            "project:membership-action",
            kwargs={"project_id": self.project.pk},
        )


    @cached_property
    def environment_containers(self):
        bindings = self.project.containerbindings.all()
    
        containers = [
            binding.container
            for binding in bindings
            if binding.container.user_id == self.user.pk
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
            and self.project.preferred_image_id is not None
            and not self.has_environment_containers
        )
    
    
    @property
    def default_environment_disabled_reason(self):
        if self.has_environment_containers:
            return None
    
        if not self.can_create_environment:
            return "You do not have permission to create an environment."
    
        if self.project.preferred_image_id is None:
            return "Select a preferred image first."
    
        return None

    @property
    def preferred_image_label(self):
        if self.project.preferred_image:
            return self.project.preferred_image.short_name
        return "No preferred image"


