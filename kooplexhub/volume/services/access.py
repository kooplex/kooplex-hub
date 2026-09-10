from dataclasses import dataclass

from ..models import (
    Volume,
    UserVolumeBinding,
)

# Volume access policy
###########################
# owner/admin
#     visible=yes
#     mountable=yes
#     manageable=yes
#     writable=yes
# 
# ATTACHMENT, non-owner
#     visible=yes
#     mountable=yes
#     manageable=no
#     writable=no
# 
# PUBLIC dataset, non-owner
#     visible=yes
#     mountable=yes
#     manageable=no
#     writable=volume.allow_shared_write
# 
# PRIVATE dataset
#     owner/admin or explicit UserVolumeBinding -> access
#     otherwise none
# 
# INTERNAL dataset
#     owner/admin -> access
#     OR user collaborates on one of owner's projects
#        to which volume is bound
#     OR user belongs to one of owner's courses
#        to which volume is bound

@dataclass(frozen=True)
class VolumeAccess:
    visible: bool
    mountable: bool
    manageable: bool
    writable: bool
    reason: str = ""

    @property
    def read_only(self) -> bool:
        return self.mountable and not self.writable


def _explicit_binding(volume, user):
    return (
        volume.userbindings
        .filter(user=user)
        .only("role")
        .first()
    )


def _is_owner(binding) -> bool:
    return (
        binding is not None
        and binding.role == UserVolumeBinding.Role.OWNER
    )


def _is_manager(binding) -> bool:
    return (
        binding is not None
        and binding.role in {
            UserVolumeBinding.Role.OWNER,
            UserVolumeBinding.Role.ADMIN,
        }
    )


def _has_internal_project_access(volume, user, owner) -> bool:
    return volume.projectbindings.filter(
        project__userbindings__user=owner,
        project__userbindings__role="creator",
    ).filter(
        project__userbindings__user=user,
    ).exists()


def _has_internal_course_access(volume, user, owner) -> bool:
    from education.models import VolumeCourseBinding  #FIXME: add related_name

    return VolumeCourseBinding.objects.filter(
        volume=volume,
        course__userbindings__user=owner,
        course__userbindings__is_teacher=True,
    ).filter(
        course__userbindings__user=user,
    ).exists()


def get_volume_owner(volume):
    binding = (
        volume.userbindings
        .filter(role=UserVolumeBinding.Role.OWNER)
        .select_related("user")
        .first()
    )

    return binding.user if binding else None


def resolve_volume_access(*, volume, user) -> VolumeAccess:
    if not user or not user.is_authenticated:
        return VolumeAccess(
            visible=False,
            mountable=False,
            manageable=False,
            writable=False,
            reason="Authentication required.",
        )

    if user.is_superuser:
        return VolumeAccess(
            visible=True,
            mountable=volume.is_present,
            manageable=True,
            writable=True,
            reason="Superuser access.",
        )

    binding = _explicit_binding(volume, user)

    if _is_owner(binding):
        return VolumeAccess(
            visible=True,
            mountable=volume.is_present,
            manageable=True,
            writable=True,
            reason="Volume owner.",
        )

    if binding and binding.role == UserVolumeBinding.Role.ADMIN:
        return VolumeAccess(
            visible=True,
            mountable=volume.is_present,
            manageable=True,
            writable=volume.allow_shared_write,   #FIXME: TODO if stated in conf and RW access to grant let it be True
            reason="Volume administrator.",
        )

    if volume.scope == Volume.Scope.ATTACHMENT:
        return VolumeAccess(
            visible=True,
            mountable=volume.is_present,
            manageable=False,
            writable=False,
            reason="Public attachment.",
        )

    if volume.scope == Volume.Scope.PUBLIC:
        return VolumeAccess(
            visible=True,
            mountable=volume.is_present,
            manageable=False,
            writable=volume.allow_shared_write,
            reason="Public volume.",
        )

    if volume.scope == Volume.Scope.PRIVATE:
        if binding is not None:
            return VolumeAccess(
                visible=True,
                mountable=volume.is_present,
                manageable=False,
                writable=volume.allow_shared_write,
                reason="Explicit private-volume access.",
            )

        return VolumeAccess(
            visible=False,
            mountable=False,
            manageable=False,
            writable=False,
            reason="Private volume.",
        )

    if volume.scope == Volume.Scope.INTERNAL:
        owner = get_volume_owner(volume)

        if owner is None:
            return VolumeAccess(
                visible=False,
                mountable=False,
                manageable=False,
                writable=False,
                reason="Internal volume has no owner.",
            )

        allowed = (
            _has_internal_project_access(volume, user, owner)
            or _has_internal_course_access(volume, user, owner)
        )

        if allowed:
            return VolumeAccess(
                visible=True,
                mountable=volume.is_present,
                manageable=False,
                writable=volume.allow_shared_write,
                reason="Access inherited through project/course membership.",
            )

    return VolumeAccess(
        visible=False,
        mountable=False,
        manageable=False,
        writable=False,
        reason="No volume access.",
    )


def can_mount_volume(*, volume, user) -> bool:
    return resolve_volume_access(
        volume=volume,
        user=user,
    ).mountable


def volume_mount_read_only(*, volume, user) -> bool:
    access = resolve_volume_access(
        volume=volume,
        user=user,
    )

    if not access.mountable:
        raise PermissionError(
            f"User may not mount volume {volume.pk}."
        )

    return access.read_only



