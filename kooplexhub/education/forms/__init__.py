from .create import (
    CourseCreateForm,
)
from .widgets import (
    CourseNameForm,
    CourseDescriptionForm,
)
from .preferred_image import (
    CoursePreferredImageForm,
)
#from .mounts import (
#    CourseMountsForm,
#)
#from .members import (
#    CourseMembersForm,
#)
#FIXME:
from .assignment import FormAssignment, FormAssignmentList, FormAssignmentConfigure
__all__ = [
    "CourseCreateForm",

    "CourseNameForm",
    "CourseDescriptionForm",
    "CoursePreferredImageForm",
#    "CourseMountsForm",
#    "CourseMembersForm",
]
