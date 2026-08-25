class AssignmentPresenter:

    def __init__(self, assignment, course_ui):
        self.assignment = assignment
        self.course_ui = course_ui

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
