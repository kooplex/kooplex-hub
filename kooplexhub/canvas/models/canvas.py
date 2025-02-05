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

    def check_connection(self):
        api = CanvasAPI(self.token)
        return api.check_connection()              

    def get_courses(self):
        '''
        Retrieves user's own courses from Canvas vai the API using the user's canvas token
        Compare already existing courses
        '''
        api = CanvasAPI(self.token)
        courses = api.get_user_courses()
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
    #user = models.ForeignKey(User, on_delete = models.CASCADE, null = False)
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
        api = CanvasAPI(token)
        #return api.get_course_students(self.canvas_course_id)
        #[{'id': 173519, 'name': 'Berekméri Evelin (N6FGSV)', 'created_at': '2016-10-13T01:07:50+02:00', 'sortable_name': 'Berekméri Evelin (N6FGSV)', 'short_name': 'Berekméri Evelin (N6FGSV)'},  ...]
        for record in api.get_course_students(self.canvas_course_id):
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
        api = CanvasAPI(token)
        #return api.get_course_students(self.canvas_course_id)
        #[{'id': 173519, 'name': 'Berekméri Evelin (N6FGSV)', 'created_at': '2016-10-13T01:07:50+02:00', 'sortable_name': 'Berekméri Evelin (N6FGSV)', 'short_name': 'Berekméri Evelin (N6FGSV)'},  ...]
        for record in api.get_course_teachers(self.canvas_course_id):
            user=User.objects.filter(username=neptun(record['name'])).first()
            if user:
                yield user

    def get_course_assignments(self):
        '''
        Retrieves assignments (per user ids from Canvas via the API using the user's canvas token
        Creates an assignment and downloads/shows all related files into it
        '''
        return api.get_course_assignments(self.canvas_course_id)

    def get_grades(self):
        '''
        Retrieves grades (per user ids from Canvas via the API using the user's canvas token
        '''
        return api.get_course_grades(self.canvas_course_id)

    def upload_results(self):
        pass

    
