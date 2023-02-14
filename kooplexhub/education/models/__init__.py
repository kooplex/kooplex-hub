from education.models.course import Course, CourseCode, UserCourseBinding, UserCourseCodeBinding
from education.models.coursecontainerbinding import CourseContainerBinding
from education.models.assignment import Assignment, UserAssignmentBinding
from education.models.group import CourseGroup,  UserCourseGroupBinding

from education.models.course_signals import create_course, delete_course, add_usercourse, delete_usercourse
from education.models.assignment_signals import delete_userassignment
