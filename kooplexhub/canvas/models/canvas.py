from typing import Any
from django.db import models
from education.models import Course, UserCourseBinding
from canvas.canvasapi import CanvasAPI

from django.contrib.auth.models import User
from hub.models import Token

# Mechanism:
# user contacts Canvas
# get list of courses
# choose one to create a local Course for it
# After education/model/course is created 

# Create your models here.
class Canvas(models.Model):
    '''
    defines a connection to the Canvas API via the token
    '''
    user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
    token = models.ForeignKey(Token, on_delete = models.CASCADE, null = False)

    # def __init__(self, *args: Any, **kwargs: Any) -> None:
    #     super().__init__(*args, **kwargs)
    #     self.api = CanvasAPI(self.token)

    @property
    def api(self):
        return CanvasAPI(self.token)

    def check_connection(self):        
        return self.api.check_connection()              

    def get_courses(self):
        '''
        Retrieves user's own courses from Canvas vai the API using the user's canvas token
        Compare already existing courses
        '''
        courses = self.api.get_user_courses()
        return courses
    
    # def create_course(self, tmp_course):
    #     '''
    #     Creates a local course based on the course or course_id
    #     '''
    #     api = CanvasAPI(self.token)
    #     if type(tmp_course) == int:
    #         tmp_course = api.get_user_courses(tmp_course)

    #     # Create a Course first
    #     folder = f"canvas_{tmp_course['id']}"
    #     course = Course.objects.create(name=tmp_course['name'], folder=folder, description=tmp_course['course_code'])


    #     is_teacher = False
    #     if tmp_course['enrollments'][0]['type'] == 'teacher':
    #         is_teacher = True
    #     canvas_course = CanvasCourse.objects.create(name=tmp_course['name'],                                                   
    #                                                 course=course)
    #     user_course = UserCourseBinding.objects.create(user=self.user, course=canvas_course.course, is_teacher=is_teacher)
    #     return canvas_course

class CanvasCourse(models.Model):
    '''
    And extended class based on education/course
    '''
    
    name = models.CharField(max_length = 200, null = False)
    canvas_course_id = models.IntegerField(null = False)
    canvas = models.ForeignKey(Canvas, on_delete = models.CASCADE, null = False)
    course = models.ForeignKey(Course, on_delete = models.CASCADE, null = False)
    #course = models.OneToOneField(Course, on_delete=models.CASCADE, null=True, blank=True)

    # def __init__(self, *args, **kwargs):
    #     super(CanvasCourse, self).__init__(*args, **kwargs)
    #     if not self.course:
    #         folder = f"canvas_{self.user.id}"
    #         self.course = Course.objects.create(name=self.name, user=self.user, folder=folder)
        

    def __str__(self):
        return self.name

    def get_course_students(self, token):
        '''
        Retrieves user ids from Canvas via the API using the user's canvas token
        '''
        import re
        from django.contrib.auth.models import User
        neptun=lambda x: re.split(r'.*\((.{6})\)', x)[1].lower()
        
        #return api.get_course_students(self.canvas_course_id)
        #[{'id': 173519, 'name': 'Berekméri Evelin (N6FGSV)', 'created_at': '2016-10-13T01:07:50+02:00', 'sortable_name': 'Berekméri Evelin (N6FGSV)', 'short_name': 'Berekméri Evelin (N6FGSV)'},  ...]
        for record in self.canvas.api.get_course_students(self.canvas_course_id):
            user=User.objects.filter(username=neptun(record['name'])).first()
            if user:
                yield user

    def get_course_teachers(self, token):
        '''
        Retrieves teachers ids from Canvas via the API using the user's canvas token
        '''
        import re
        from django.contrib.auth.models import User
        neptun=lambda x: re.split(r'.*\((.{6})\)', x)[1].lower()

        #return api.get_course_students(self.canvas_course_id)
        #[{'id': 173519, 'name': 'Berekméri Evelin (N6FGSV)', 'created_at': '2016-10-13T01:07:50+02:00', 'sortable_name': 'Berekméri Evelin (N6FGSV)', 'short_name': 'Berekméri Evelin (N6FGSV)'},  ...]
        for record in self.canvas.api.get_course_teachers(self.canvas_course_id):
            user=User.objects.filter(username=neptun(record['name'])).first()
            if user:
                yield user

    def get_course_assignments(self):
        '''
        Retrieves assignments (per user ids from Canvas via the API using the user's canvas token
        Creates an assignment and downloads/shows all related files into it
        '''
    
        return self.canvas.api.get_course_assignments(self.canvas_course_id)

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
        return self.canvas.api.get_course_grades(self.canvas_course_id)

    def upload_results(self):
        pass

    
