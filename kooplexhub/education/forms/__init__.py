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
from .mounts import (
    CourseMountsForm,
)
from .members import (
    CourseMembersForm,
)
from .assignment import (
    AssignmentScheduleForm,
)
__all__ = [
    "CourseCreateForm",

    "CourseNameForm",
    "CourseDescriptionForm",
    "CoursePreferredImageForm",
    "CourseMountsForm",
    "CourseMembersForm",

    "AssignmentScheduleForm",
]
