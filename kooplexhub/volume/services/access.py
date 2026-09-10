from dataclasses import dataclass

from ..models import Volume

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


#def resolve_volume_access(*, volume, user) -> VolumeAccess:


def volume_is_read_only_for(volume, user):
    if volume_is_owner_or_admin(volume, user):
        return False

    if volume.scope == Volume.Scope.ATTACHMENT:
        return True

    return not volume.allow_shared_write

