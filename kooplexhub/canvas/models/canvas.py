import logging
from django.db import models
from education.models import Course, UserCourseBinding
from ..canvasapi import CanvasAPI

from django.contrib.auth import get_user_model
from hub.models import Token

logger = logging.getLogger(__name__)
User = get_user_model()

class CanvasCourse(models.Model):
    '''
    And extended class based on education/course
    '''
    name = models.CharField(max_length = 200, null = False)
    canvas_course_id = models.IntegerField(null = False)  # The course id in Canvas
    course = models.ForeignKey(Course, on_delete = models.CASCADE, null = False)
    creator = models.ForeignKey(User, on_delete = models.CASCADE, null = False)

    def __str__(self):
        return self.name

    # factory
    @staticmethod
    def create(user_id, canvas_id, course):
        from hub.models import Token
        token = Token.objects.filter(user__id = user_id, type__name='Canvas').first()
        api=CanvasAPI(token)
        r=api.get_user_courses()
        canvas_courses = filter(lambda x: x['id']==canvas_id, r)
        if not canvas_courses:
            logger.error(f'user {token.user} has no access to canvas course ({canvas_id})')
            return
        cc=list(canvas_courses)[0]
        logger.critical(list(canvas_courses))
        canvascourse=CanvasCourse.objects.create(name=cc['name'], canvas_course_id=canvas_id, course=course, creator=token.user)
        for cs in canvascourse.get_course_students(token):
            UserCourseBinding.objects.create(course=course, user=cs)
        for ct in canvascourse.get_course_teachers(token):
            UserCourseBinding.objects.get_or_create(course=course, user=ct, is_teacher=True)
        return canvascourse

    def get_course_students(self, token):
        '''
        Retrieves user ids from Canvas via the API using the user's canvas token
        '''
        import re
        neptun=lambda x: re.split(r'.*\((.{6})\)', x)[1].lower()
        
        #return api.get_course_students(self.canvas_course_id)
        #[{'id': 173519, 'name': 'Minta Sandor (TRU73I)', 'created_at': '2016-10-13T01:07:50+02:00', 'sortable_name': 'Minta Sandor (TRU73I)', 'short_name': 'Minta Sandor (TRU73I)'},  ...]
        api=CanvasAPI(token)
        for record in api.get_course_students(self.canvas_course_id):
            user=User.objects.filter(username=neptun(record['name'])).first()
            if user:
                yield user

    def get_course_teachers(self, token):
        '''
        Retrieves teachers ids from Canvas via the API using the user's canvas token
        '''
        import re
        neptun=lambda x: re.split(r'.*\((.{6})\)', x)[1].lower()

        #return api.get_course_students(self.canvas_course_id)
        #[{'id': 173519, 'name': 'Minta Sandor (TRU73I)', 'created_at': '2016-10-13T01:07:50+02:00', 'sortable_name': 'Minta Sandor (TRU73I)', 'short_name': 'Minta Sandor (TRU73I)'},  ...]
        api=CanvasAPI(token)
        for record in api.get_course_teachers(self.canvas_course_id):
            user=User.objects.filter(username=neptun(record['name'])).first()
            if user:
                yield user

    def get_course_assignments(self):
        '''
        Retrieves assignments (per user ids from Canvas via the API using the user's canvas token
        Creates an assignment and downloads/shows all related files into it
        '''
        api=CanvasAPI(token)
        return api.get_course_assignments(self.canvas_course_id)

# Peldanak beraktam ide egy assignment json-t
        """
{
    "id": 393813,
    "description": "<p>valami<br><a class=\"instructure_file_link\" title=\"Ex-1A-ImageSegmentation.ipynb\" href=\"https://canvas.elte.hu/courses/52749/files/3483851/download?verifier=oPX9Nc5UAdYIqDCatxe7HEkl11tpyddhljsTuKTf&amp;wrap=1\" data-api-endpoint=\"https://canvas.elte.hu/api/v1/courses/52749/files/3483851\" data-api-returntype=\"File\">Ex-1A-ImageSegmentation.ipynb</a></p>",
    "due_at":  '2025-02-10T22:59:59Z',
    "unlock_at": null,
    "lock_at": '2025-05-14T21:59:59Z',
    "points_possible": 12.0,
    "grading_type": "points",
    "assignment_group_id": 81560,
    "grading_standard_id": null,
    "created_at": "2025-01-30T12:00:20Z",
    "updated_at": "2025-02-05T01:32:23Z",
    "peer_reviews": false,
    "automatic_peer_reviews": false,
    "position": 1,
    "grade_group_students_individually": false,
    "anonymous_peer_reviews": false,
    "group_category_id": null,
    "post_to_sis": false,
    "moderated_grading": false,
    "omit_from_final_grade": false,
    "intra_group_peer_reviews": false,
    "anonymous_instructor_annotations": false,
    "graders_anonymous_to_graders": false,
    "grader_count": 0,
    "grader_comments_visible_to_graders": true,
    "final_grader_id": null,
    "grader_names_visible_to_final_grader": true,
    "allowed_attempts": -1,
    "anonymous_grading": false,
    "secure_params": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJsdGlfYXNzaWdubWVudF9pZCI6ImZiMDQ3YTYxLTdlNDUtNDRiYS04YjIyLWIwYzY4YTNiYTZjYSJ9.6p4EX5RTCGuGUmQoiDZXNRLRLMjWFtdZ1IljY4JQhOM",
    "course_id": 52749,
    "name": "testproject",
    "submission_types": ["online_upload"],
    "has_submitted_submissions": false,
    "due_date_required": false,
    "max_name_length": 255,
    "in_closed_grading_period": false,
    "is_quiz_assignment": false,
    "can_duplicate": true,
    "original_course_id": null,
    "original_assignment_id": null,
    "original_assignment_name": null,
    "original_quiz_id": null,
    "workflow_state": "published",
    "muted": false,
    "html_url": "https://canvas.elte.hu/courses/52749/assignments/393813",
    "has_overrides": false,
    "needs_grading_count": 0,
    "published": true,
    "unpublishable": true,
    "only_visible_to_overrides": false,
    "locked_for_user": false,
    "submissions_download_url": "https://canvas.elte.hu/courses/52749/assignments/393813/submissions?zip=1",
    "anonymize_students": false,
    "require_lockdown_browser": false
}
    """


    def get_grades(self):
        '''
        Retrieves grades (per user ids from Canvas via the API using the user's canvas token
        '''
        api=CanvasAPI(token)
        return api.get_course_grades(self.canvas_course_id)

    def upload_results(self):
        pass

    
