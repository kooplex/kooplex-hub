from .name import (
    CourseNameDisplayView,
    CourseNameEditView,
    CourseNameUpdateView,
    CourseCreateNameValidateView,
)
from .description import (
    CourseDescriptionDisplayView,
    CourseDescriptionEditView,
    CourseDescriptionUpdateView,
    CourseCreateDescriptionValidateView,
)
from .preferred_image import (
    CoursePreferredImageDisplayView,
    CoursePreferredImageChangeView,
    CoursePreferredImageUpdateView,
    CourseCreatePreferredImageValidateView,
)
#from .mounts import (
#    CourseMountsDisplayView,
#    CourseMountsModalView,
#    CourseMountsUpdateView,
#)
from .members import (
#    CourseMembersSummaryView,
#    CourseMembersModalView,
#    CourseMembersChangeView,
#    CourseMemberSearchView,
#    CourseMemberRowView,
    CourseCreateMemberSearchView,
    CourseCreateMemberSearchView as CourseMemberSearchView, #FIXME
    CourseCreateMemberRowView,
#    CourseMembersUpdateView,
)
#from .environment import (
#    CourseEnvironmentTabView,
#    CourseDefaultEnvironmentCreateView,
#)


__all__ = [
    "CourseNameDisplayView",
    "CourseNameEditView",
    "CourseNameUpdateView",
    "CourseCreateNameValidateView",

    "CourseDescriptionDisplayView",
    "CourseDescriptionEditView",
    "CourseDescriptionUpdateView",
    "CourseCreateDescriptionValidateView",

    "CoursePreferredImageDisplayView",
    "CoursePreferredImageEditView",
    "CoursePreferredImageChangeView",
    "CourseCreatePreferredImageValidateView",
    
#    "CourseMountsDisplayView",
#    "CourseMountsModalView",
#    "CourseMountsUpdateView",
#
#    "CourseMembersSummaryView",
#    "CourseMembersModalView",
#    "CourseMembersChangeView",
    "CourseMemberSearchView",
#    "CourseMemberRowView",
#    "CourseMembersUpdateView",
    "CourseCreateMemberSearchView",
    "CourseCreateMemberRowView",
#
#    "CourseEnvironmentTabView",
#    "CourseDefaultEnvironmentCreateView",
]

