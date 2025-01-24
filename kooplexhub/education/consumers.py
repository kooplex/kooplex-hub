import logging
import json
import threading

import pandas
import numpy #FIXME: with newer pandas we may fall back to pandas.NA
from django_pandas.io import read_frame
from django.template.loader import render_to_string

from asgiref.sync import sync_to_async

from education.models import UserAssignmentBinding, Assignment, UserCourseBinding, CourseContainerBinding
from education.forms import TableAssignmentConf

from hub.util import is_model_field, SyncSkeleton, AsyncSkeleton
from .models import Course
from volume.models import Volume

logger = logging.getLogger(__name__)

class AssignmentConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        course_id = parsed.get('course_id')
        # authorize
        course=UserCourseBinding.objects.get(user__id=self.userid, course__id=course_id, is_teacher=True).course
        # folder for new assignment
        folders=course.dir_assignmentcandidate()
        # assignment manager table
        a=Assignment.objects.filter(course=course_id)
        t=TableAssignmentConf(a)  #FIXME rename to TableAssignmentHandler
        # calculate students' scores
        #FIXME pandas version may be too old?
        #dfm = read_frame(UserAssignmentBinding.objects.filter(assignment__course__id = course_id)).fillna(pandas.NA)
        dfm = read_frame(UserAssignmentBinding.objects.filter(assignment__course__id = course_id)).fillna(numpy.nan)
        dfm=dfm[['user', 'assignment', 'score']]
        if not dfm.empty:
            table = dfm.pivot(index = "user", columns = "assignment", values = "score")
            table.columns = [tc.split("Assignment ")[1].split(" (")[0] for tc in table.columns]  #FIXME: not a very nice way to parse
            points = dfm.fillna(0).groupby(by="user").agg("sum")[["score"]].rename(columns={"score":"Total points"})
            result = pandas.merge(left=table, right=points, left_on="user", right_on="user", how="inner")
            t_score = result.to_html(classes = "table table-bordered table-striped text-center", index_names = False, justify = "center", na_rep = "—", border = None)
        else:
            t_score=f"<h6 class="">There are no assignments in this course.</h6>"
        self.send(text_data=json.dumps({
            "feedback": "Assignment list is refreshed",
            "f_new": render_to_string('widgets/form_new_assignment.html', {'course': course, 'folders': folders, 'table': TableAssignmentConf([Assignment()])}),
            "t_assignment": render_to_string('django_table.html', {'table':t}),
            "t_score": t_score,
            }))



#################

class CourseGetContainersConsumer(SyncSkeleton):
    def receive(self, text_data):
        from django.urls import reverse
        parsed = json.loads(text_data)
        logger.debug(parsed)
        #assert parsed.get('request')=='configure-project', "wrong request"
        courseid = parsed.get('pk')
        bindings = CourseContainerBinding.objects.filter(container__user__id=self.userid, course__id=courseid)
        ucb=UserCourseBinding.objects.get(user__id=self.userid, course__id=courseid)
        link_autocreate=reverse('education:autoaddcontainer', args=[ucb.id,])
        message_back = {
            "feedback": f"Container list refreshed",
            "response": render_to_string("widgets/widget_containertable.html", {"containers": map(lambda o: o.container, bindings), "link_autocreate": link_autocreate }),
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back))


class HandinConsumer(AsyncSkeleton):
    identifier='handin'
    async def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        cid = int(parsed.get('pk'))
        idlist = parsed.get('uabs')
        logger.info(idlist)
        bindings = await sync_to_async(list)(UserAssignmentBinding.objects.filter(user__id=self.userid, id__in=idlist, assignment__course__id=cid))
        for b in bindings:
            await sync_to_async(b.collect)()
            await self.send(text_data=json.dumps({"feedback": f'A snapshot is being prepared for {b.assignment.name}.' }))


from .models import VolumeCourseBinding
class CourseConfigConsumer(SyncSkeleton):
    def get_course(self, course_id):
        c=Course.objects.get(id = course_id)
        assert self.userid in map(lambda o:o.id, c.teachers), "You are not a teacher to config"
        return c

    def receive(self, text_data):
        from container.models import Image
        parsed = json.loads(text_data)
        logger.debug(parsed)
        response = {
            "success": {},
            "failed": {},
        }
        pk = parsed.get('pk')
        changes = parsed.get('changes')
        if pk == "":
            course=Course.objects.create(name=changes.pop('name'), preferred_image_id=changes.pop('image'), description=changes.pop('description'))
            binding=UserCourseBinding.objects.create(user_id=self.get_userid(), course=course)
            response["reloadpage"]=True
        else:
            cid = int(pk)
            course = self.get_course(cid)
        # Add students and teachers
        users=changes.pop('users', [])
        if users:
            teachers=changes.pop('marked', [])
            for u in users:
                is_teacher=u in teachers
                b=UserCourseBinding.objects.filter(user__id=u, course=course)
                if b:
                    b=b.first()
                    if b.is_teacher==is_teacher:
                        continue
                    # if student/teacher state changes, delete old relationship instance
                    b.delete()
                UserCourseBinding.objects.create(user_id=u, course=course, is_teacher=is_teacher)
            # Remove students and teachers
            users.append(self.userid)  # make sure caller is not removed
            UserCourseBinding.objects.filter(course=course).exclude(user__id__in=users).delete()
        # Iterate over the changes and try to update the model instance
        for field, new_value in changes.items():
            if field == 'image':
                new_value=Image.objects.get(id=new_value)
                field='preferred_image'
            # Check if the field is a valid attribute of the model
            if is_model_field(course, field):
                old_value = getattr(course, field)
                try:
                    # Try assigning the new value to the model's field
                    setattr(course, field, new_value)
                    # Run Django's model validation for the field
                    course.full_clean(validate_unique=True, exclude=[f for f in changes.keys() if f != field])
                    # If no exception was raised, add it to the success response
                    response["success"][field] = new_value
                except ValidationError as e:
                    # Validation failed, record the error message
                    response["failed"][field] = { "error": str(e), "value": old_value }
            elif field=="volumes":
                for volume in Volume.objects.filter(id__in=new_value):
                    VolumeCourseBinding.objects.get_or_create(volume=volume, course=course)
                VolumeCourseBinding.objects.filter(course=course).exclude(volume__id__in=new_value).delete()
                response["success"]['volumes']=VolumeCourseBinding.objects.filter(course=course)
            else:
                # Attribute does not exist on the model
                logger.error(f"Course model attribute {field} does not exist.")
        # Save the instance if there are any successful changes
        logger.debug(response)
        if response["success"]:
            course.save()
        message_back = {
            "feedback": f"Course {course.name} is configured",
            "response": response,
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back))
