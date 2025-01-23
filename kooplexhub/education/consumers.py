import logging
import json
import threading

import pandas
from django_pandas.io import read_frame
from django.template.loader import render_to_string

from asgiref.sync import sync_to_async

from education.models import UserAssignmentBinding, Assignment, UserCourseBinding, CourseContainerBinding
from education.forms import TableAssignmentHandle

from hub.util import is_model_field, SyncSkeleton, AsyncSkeleton
from .models import Course

logger = logging.getLogger(__name__)

#from django.db.models.query import QuerySet
#
#class AssignmentConsumer(SyncConsumer):
#    def receive(self, text_data):
#        parsed = json.loads(text_data)
#        logger.debug(parsed)
#        userid = parsed.get('user_id')
#        assignment_id = parsed.get('assignment_id')
#        group_id = parsed.get('group_id')
#        # authorize
#        assignment = Assignment.objects.get(id = assignment_id)
#        UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
#        if group_id == "all":
#            students = [ b.user for b in assignment.course.studentbindings ]
#        else:
#            groups = { 'n' if g is None else str(g.id): students for g, students in assignment.course.groups.items() }
#            students = groups[group_id]
#        bindings_present = list(UserAssignmentBinding.objects.filter(assignment = assignment, user__in = students))
#        students_present = [ b.user for b in bindings_present ]
#        bindings = [ UserAssignmentBinding(user = u, assignment = assignment) for u in students if u not in students_present ]
#        bindings.extend(bindings_present)
#        t = TableAssignmentHandle(bindings)
#        self.send(text_data = json.dumps(f"""<h6 class="">Handle assignment {assignment.name}</h6>{t.as_html(None)}"""))
#
#
#class AssignmentSummaryConsumer(SyncConsumer):
#    def receive(self, text_data):
#        parsed = json.loads(text_data)
#        logger.debug(parsed)
#        self.send(text_data = json.dumps(parsed)) #ping
#        userid = parsed.get('user_id')
#        courseid = parsed.get('course_id')
#        # authorize
#        course = UserCourseBinding.objects.get(user__id = userid, course__id = courseid, is_teacher = True).course
#        bindings = UserAssignmentBinding.objects.filter(assignment__course = course)
#        if bindings.count() == 0:
#            self.send(text_data = json.dumps(f"""<h6 class="">There are no assignments in this course {course.name}</h6>"""))
#            return None
#        dfm = read_frame(bindings)
#        table = dfm.pivot(index = "user", columns = "assignment", values = "score")
#        table.columns = [tc.split("Assignment ")[1].split(" (")[0] for tc in table.columns]
#        points = dfm.fillna(0).groupby(by="user").agg("sum")[["score"]].rename(columns={"score":"Total points"})
#        result = pandas.merge(left=table, right=points, left_on="user", right_on="user", how="inner")
#        t = result.to_html(classes = "table table-bordered table-striped text-center", index_names = False, justify = "center", na_rep = "—", border = None)
#        self.send(text_data = json.dumps(f"""<h6 class="">The score table for course {course.name}</h6>{t}"""))

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


class CourseConfigConsumer(SyncSkeleton):
    from container.models import Image
    def get_course(self, course_id):
        c=Course.objects.get(id = course_id)
        assert self.userid in map(lambda o:o.id, c.teachers), "You are not a teacher to config"
        return c

    def receive(self, text_data):
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
        # Iterate over the changes and try to update the model instance
        for field, new_value in changes.items():
            if field == 'image':
                new_value=Image.objects.get(id=new_value)
                field='preferred_image'
            # Check if the field is a valid attribute of the model
            if is_model_field(container, field):
                old_value = getattr(container, field)
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
#            elif field == 'projects':
#                for project in Project.objects.filter(id__in = new_value):
#                    ProjectContainerBinding.objects.get_or_create(project = project, container = container)
#                ProjectContainerBinding.objects.filter(container = container).exclude(project__id__in = new_value).delete()
#                response["success"]['projects']=ProjectContainerBinding.objects.filter(container = container)
#                restart.append("project mounts changed")
#            elif field == 'courses':
#                for course in Course.objects.filter(id__in = new_value):
#                    CourseContainerBinding.objects.get_or_create(course = course, container = container)
#                CourseContainerBinding.objects.filter(container = container).exclude(course__id__in = new_value).delete()
#                response["success"]['courses']=CourseContainerBinding.objects.filter(container = container)
#                restart.append("course mounts changed")
#            elif field == 'volumes':
#                for volume in Volume.objects.filter(id__in = new_value):
#                    VolumeContainerBinding.objects.get_or_create(volume = volume, container = container)
#                VolumeContainerBinding.objects.filter(container = container).exclude(volume__id__in = new_value).delete()
#                response["success"]['volumes']=VolumeContainerBinding.objects.filter(container = container)
#                restart.append("volume mounts changed")
#            else:
#                # Attribute does not exist on the model
#                logger.error(f"Container model attribute {field} does not exist.")
#        # Save the instance if there are any successful changes
        if response["success"]:
            course.save()
        message_back = {
            "feedback": f"Course {course.name} is configured",
            "response": response,
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back))
