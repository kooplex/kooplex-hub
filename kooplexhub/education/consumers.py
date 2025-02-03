import logging
import json
import threading

import pandas
import numpy #FIXME: with newer pandas we may fall back to pandas.NA
from django_pandas.io import read_frame
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from asgiref.sync import sync_to_async

from education.models import UserAssignmentBinding, Assignment, UserCourseBinding, CourseContainerBinding
from education.forms import TableAssignmentConf

from hub.util import is_model_field, SyncSkeleton, AsyncSkeleton
from .models import Course
from volume.models import Volume

logger = logging.getLogger(__name__)

class AssignmentConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed=json.loads(text_data)
        logger.debug(parsed)
        course_id=parsed.get('course_id')
        # authorize
        course=UserCourseBinding.objects.get(user__id=self.userid, course__id=course_id, is_teacher=True).course
        query=parsed.get('query')
        if query=='list':
            self.refresh_list(course)
        elif query=='configure':
            self.delete(course, parsed.get('remove'))
            self.configure(course, parsed.get('data'))
            self.reassign(course, parsed.get('reassign'))
            self.collect(course, parsed.get('collect'))
            self.handout(course, parsed.get('handout'))
            self.refresh_list(course)

    def refresh_list(self, course):
        # folder for new assignment
        folders=course.dir_assignmentcandidate()
        # get canvas assignments too? if it is a course canvas
        try:
            if course.canvas_course_id:
                print(course.get_course_assignments())
        except: 
            pass
        # canvas.api.get_course_assignment
        # assignment manager table
        a=Assignment.objects.filter(course=course)
        t=TableAssignmentConf(a)
        # calculate students' scores
        #FIXME pandas version may be too old?
        #dfm = read_frame(UserAssignmentBinding.objects.filter(assignment__course = course)).fillna(pandas.NA)
        dfm = read_frame(UserAssignmentBinding.objects.filter(assignment__course = course)).fillna(numpy.nan)
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
            "f_new": render_to_string('widgets/form_new_assignment.html', {'course': course, 'folders': folders, 'table': TableAssignmentConf([Assignment()], exclude_columns=['manage', 'delete'])}),
            "t_assignment": render_to_string('django_table.html', {'table':t}),
            "t_score": t_score,
            }))

    def configure(self, course, configlist):
        for c in configlist:
            assignment_id=c['id']
            chg=c['changed']
            if assignment_id=='None':  #FIXME: ""
                a=Assignment.objects.create(course=course, creator_id=self.userid, **chg)
                a.snapshot()
                #FIXME: feedback message
            else:
                a=Assignment.objects.get(id=assignment_id, course=course)
                for field, value in chg.items():
                    if value=="":
                        value=None
                    old=getattr(a, field)
                    setattr(a, field, value)
                    try:
                        a.full_clean()
                    except ValidationError as e:
                        # fixme feedback error
                        setattr(a, field, old)
                a.save()
                #FIXME: feedback message

    def delete(self, course, deletelist):
        Assignment.objects.filter(course=course, id__in=deletelist).delete()

    def handout(self, course, handoutlist):
        for a in Assignment.objects.filter(course=course, id__in=handoutlist):
            a.handout()

    def collect(self, course, collectlist):
        for a in Assignment.objects.filter(course=course, id__in=collectlist):
            a.collect()

    def reassign(self, course, reassignlist):
        for a in Assignment.objects.filter(course=course, id__in=reassignlist):
            a.reassign()


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
    identifier_='handin'
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
        from kooplexhub.lib.libbase import standardize_str
        import datetime
        parsed = json.loads(text_data)
        logger.debug(parsed)
        failed={}
        success=False
        pk = parsed.get('pk')
        changes = parsed.get('changes')
        if pk=="None":
            reloadpage=True
            canvas_id=changes.pop('canvasid', None)
            _name=changes.pop('name')
            _folder=f"{datetime.datetime.now().year}-{standardize_str(_name)}" #FIXME settings.py-ba át lehetne tenni, year 
            course=Course.objects.create(name=_name, preferred_image_id=changes.pop('image'), description=changes.pop('description'), folder=_folder)
            binding=UserCourseBinding.objects.create(user_id=self.get_userid(), course=course, is_teacher=True)
            if canvas_id:
                from canvas.models import CanvasCourse, Canvas
                canvas=Canvas.objects.get(user_id=self.get_userid())
                #FIXME: keep canvasname
                canvascourse=CanvasCourse.objects.create(name=course.name, canvas_course_id=canvas_id, course=course)
                for cs in canvascourse.get_course_students(canvas.token):
                    UserCourseBinding.objects.create(course=course, user=cs)
        else:
            reloadpage=False
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
                    success=True
                except ValidationError as e:
                    # Validation failed, record the error message
                    failed[field] = { "error": str(e), "value": old_value }
            elif field=="volumes":
                for volume in Volume.objects.filter(id__in=new_value):
                    VolumeCourseBinding.objects.get_or_create(volume=volume, course=course)
                VolumeCourseBinding.objects.filter(course=course).exclude(volume__id__in=new_value).delete()
                success=True
            else:
                # Attribute does not exist on the model
                logger.error(f"Course model attribute {field} does not exist.")
        # Save the instance if there are any successful changes
        if success:
            course.save()
        message_back = {
            "feedback": f"Course {course.name} is createed" if reloadpage else f"Course {course.name} is configured",
            "response": "reloadpage" if reloadpage else render_to_string("course.html", {"course": course, "user": self.scope['user'] }),
            "course_id": course.id,
        }
        logger.debug(message_back["feedback"])
        self.send(text_data=json.dumps(message_back))
