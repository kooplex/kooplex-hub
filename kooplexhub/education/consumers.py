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
from education.tables import TableAssignmentConf
from django.contrib.auth.models import User

from hub.util import SyncSkeleton, AsyncSkeleton, Config, normalize_pk
from .models import Course, VolumeCourseBinding
from volume.models import Volume

logger = logging.getLogger(__name__)

class AssignmentScoreConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed=json.loads(text_data)
        logger.debug(parsed)
        query=parsed.get('request')
        student=parsed.get('student')
        assignment=parsed.get('assignment')
        course_id=parsed.get('courseid')
        uab=UserAssignmentBinding.objects.filter(user__username=student, assignment__name=assignment, assignment__course__id=course_id).first()
        if not uab:
            logger.warn("received wrong argument list")
            return
        if query=='fetch':
            self.send(text_data=json.dumps({'student': student, 'assignment': assignment, 'score': uab.score, 'comment': uab.feedback_text}))
        elif query=='store':
            uab.score=parsed.get('score')
            uab.feedback_text=parsed.get('comment')
            uab.save()


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
            self.individual(course, parsed.get('individual'))
            self.refresh_list(course)

    def refresh_list(self, course):
        import django_tables2 as tables
        # Function to dynamically create the table class
        def create_table_class(df, editable_columns):
            table_attrs = {
                'Meta': type('Meta', (), {'attrs': {'class': 'table table-bordered table-hover mb-0'}})  # Bootstrap styling
            }
            # Dynamically add columns
            for col in df.columns:
                if col in editable_columns:
                    template = f"""
                    <span class="score-popover"
                          role="button" tabindex="0"
                          data-bs-toggle="popover" data-bs-trigger="manual"
                          data-assignment="{col}"
                          data-student="{{{{ record.user }}}}">
                      {{{{ record.{col}|default:"—" }}}}
                    </span>
                    """
                    table_attrs[col] = tables.TemplateColumn(
                        template_code=template,
                        orderable=False,
                        verbose_name=col
                    )
                else:
                    table_attrs[col] = tables.Column(orderable=False, verbose_name=col)
            # Create and return the table class
            return type('DynamicEditableTable', (tables.Table,), table_attrs)
        # folders for new assignment
        folders=course.dir_assignmentcandidate()
        # get canvas assignments too? if it is a course canvas
        from canvas.models import CanvasCourse, Canvas
        canvas_courses = []
        try:
            ccourse = CanvasCourse.objects.filter(course=course).first()
            if ccourse.canvas_course_id:
                logger.debug(f"Canvas course: {ccourse} - {ccourse.canvas_course_id}")
                canvas_courses = ccourse.get_course_assignments()                
        except Exception as e: 
            logger.debug(f"Exc {e}")

        # assignment manager table
        a=Assignment.objects.filter(course=course)
        UAbind_dict = {
            (ua.user_id, ua.assignment_id): ua.state
            for ua in UserAssignmentBinding.objects.filter(assignment__in=a)
        }
        t=TableAssignmentConf(a)
        # calculate students' scores
        #FIXME pandas version may be too old?
        #dfm = read_frame(UserAssignmentBinding.objects.filter(assignment__course = course)).fillna(pandas.NA)
        dfm = read_frame(UserAssignmentBinding.objects.filter(assignment__course = course)).fillna(numpy.nan)
        dfm=dfm[['user', 'assignment', 'score']]
        if not dfm.empty:
            try:
                table = dfm.pivot(index = "user", columns = "assignment", values = "score")
                table.columns = [tc.split("Assignment ")[1].split(" (")[0] for tc in table.columns]  #FIXME: not a very nice way to parse
                points = dfm.fillna(0).groupby(by="user").agg("sum")[["score"]].rename(columns={"score":"Total points"})
                result = pandas.merge(left=table, right=points, left_on="user", right_on="user", how="inner").reset_index()
                EditableTable = create_table_class(result, table.columns)
                t_score = EditableTable(result.fillna("—").to_dict(orient='records'))  # Convert DataFrame to Django Table
            except Exception as e:
                logger.critical(f"FIXME pivot -- {e}")
                t_score=None
        else:
            t_score=None
        self.send(text_data=json.dumps({
            "feedback": "Assignment list is refreshed",
            "f_new": render_to_string('widgets/form_new_assignment.html', {'course': course, 'folders': folders, 'table': TableAssignmentConf([Assignment()], exclude_columns=['manage', 'delete'])}),
            "t_assignment": render_to_string('django_table.html', {'table':t}),
            "t_individual": render_to_string('widgets/table_handle_individual.html', {'assignments': a, 'students': course.students, 'bindings': UAbind_dict}),
            "t_score": render_to_string('widgets/table_scores.html', {'table': t_score, "course_id": course.id}) if t_score else f"<h6 class="">There are no assignments in this course.</h6>",
            }))

    def configure(self, course, configlist):
        for c in configlist:
            assignment_id=c['id']
            chg=c['changed']
            if assignment_id=='None':  #FIXME: ""
                for att in ['valid_from', 'expires_at', 'folder']:
                    if chg.get(att, None) in ['', None]:
                        chg.pop(att)
                if not 'folder' in chg:
                    continue
                a=Assignment.objects.create(course=course, creator_id=self.userid, **chg)
                a.snapshot()
                self.send(text_data=json.dumps({"feedback": f"New assignment {a.name} registered and is queued to archive."}))
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
                        self.send(text_data=json.dumps({"feedback": f"Warning: failed to set {a.name}'s {field}, old value {old} is kept."}))
                        setattr(a, field, old)
                a.save()
                self.send(text_data=json.dumps({"feedback": f"Assignment {a.name} is configured."}))
                

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

    def individual(self, course, individual):
        for t in individual:
            b, _ = UserAssignmentBinding.objects.get_or_create(user_id=t['user_id'], assignment_id=t['assignment_id'])
            if t['todo']=='handout':
                b.handout()
            if t['todo']=='collect':
                b.collect()
            if t['todo']=='reassign':
                b.reassign()


#################



class CourseGetContainersConsumer(SyncSkeleton):
    def receive(self, text_data):
        from django.urls import reverse
        parsed = json.loads(text_data)
        logger.debug(parsed)
        #assert parsed.get('request')=='configure-project', "wrong request"
        if parsed.get('request')=='autoadd':
            usercoursebinding_id=parsed.get('pk')
            message, courseid=self.addcontainer(usercoursebinding_id)
        else:
            message=None
            courseid = parsed.get('pk')
        bindings = CourseContainerBinding.objects.filter(container__user__id=self.userid, course__id=courseid)
        ucb=UserCourseBinding.objects.get(user__id=self.userid, course__id=courseid)
        message_back = {
            "feedback": message if message else f"Container list refreshed",
            "pk": courseid,
            "response": render_to_string("container/table_control_shortcut.html", {"containers": list(map(lambda o: o.container, bindings)), "pk": ucb.id, "objectId": courseid }),
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back))

    def addcontainer(self, usercoursebinding_id):
        """
        @summary: automagically create an environment
        @param usercoursebinding_id
        """
        from kooplexhub.lib.libbase import standardize_str
        from volume.models import VolumeContainerBinding
        from container.models import Container
        try:
            ucb = UserCourseBinding.objects.get(id = usercoursebinding_id, user_id = self.userid)
            course = ucb.course
            user = ucb.user
            container, created = Container.objects.get_or_create(
                name = f'generated for {course.name}', 
                label = f'edu-{user.username}-{standardize_str(course.name)}',
                user = user,
                image = course.preferred_image
            )
            CourseContainerBinding.objects.create(course = course, container = container)
            for b in VolumeCourseBinding.objects.filter(course=course):
                VolumeContainerBinding.objects.get_or_create(container=container, volume=b.volume)
            if created:
                return f'We created a new environment {container.name} for course {course.name}.', course.id
            else:
                return f'We associated your course {course.name} with your former environment {container.name}.', course.id
        except Exception as e:
            return f'We failed -- {e}', course.id


class HandinConsumer(AsyncSkeleton):
    identifier_ = 'handin'

    async def receive(self, text_data):
        try:
            parsed = json.loads(text_data or "{}")
            bid = int(parsed.get("pk"))
        except (json.JSONDecodeError, TypeError, ValueError):
            return
        binding, assignment_name = await sync_to_async(
            lambda: (
                lambda b: (b, b.assignment.name) if b else (None, None)
            )(
                UserAssignmentBinding.objects
                .select_related("assignment")              # avoid extra query
                .filter(user_id=self.userid, id=bid)
                .first()
            )
        )()
        if binding:
            await self.send(text_data=json.dumps({
                "feedback": f"A snapshot is being prepared for assignment {assignment_name}. Hand in button disabled."
            }))
            await sync_to_async(binding.collect)()
        else:
            msg = f"Assignment binding {bid} for user_id {self.userid} does not exist"
            logger.error(msg)


class UserHandler(SyncSkeleton):
    def get_course(self, course_id):
        #FIXME: code repetition! (but modified)
        try:
            c=Course.objects.get(id = course_id)
            return c if self.userid in map(lambda o:o.id, c.teachers) else None
        except Course.DoesNotExist:
            return None

    def _chg_user_bindings(self, course, ids, marked):
        c=[]
        a=[]
        r=[]
        m=""
        for user in User.objects.filter(id__in = ids):
            if user.id==self.userid:
                # skip caller
                continue
            is_teacher=user.id in marked
            b=UserCourseBinding.objects.filter(user=user, course=course)
            if b:=b.first():
                if b.is_teacher==is_teacher:
                    continue
                # if student/teacher state changes, delete old relationship instance
                c.append(str(user))
                b.delete()
            ucb= UserCourseBinding.objects.create(user=user, course=course, is_teacher=is_teacher)
            if not str(user) in c:
                a.append(str(user))
        # Remove students and teachers
        for ucb in UserCourseBinding.objects.filter(course=course).exclude(user__id__in=ids).exclude(user__id=self.userid):
            ucb.delete()
            r.append(str(ucb.user))
        if a:
            m += "added " + ", ".join(a) + "\n"
        if r:
            m += "removed " + ", ".join(r) + "\n"
        if c:
            m += "role changed " + ", ".join(c) + "\n"
        return m

    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        course_id = normalize_pk(parsed.get('pk'))
        course = self.get_course(course_id)
        response = {
            'response': request,
            'request_id': parsed.get('request_id'),
            'pk': course_id,
        }
        if request=='parse-users-from-file':
            usernames = parsed.get('content').splitlines()
            users = User.objects.filter(username__in = usernames)
            response['ids'] = list(map(lambda u: u.id, users))
            logger.debug(response)
            self.send(text_data=json.dumps(response))
        elif request=='get-users':
            _uid = lambda b: b.user.id
            response['ids'] = list(map(_uid, UserCourseBinding.objects.filter(course=course).exclude(user__id=self.userid)))
            response['marked_ids'] = list(map(_uid, UserCourseBinding.objects.filter(course=course, is_teacher=True).exclude(user__id=self.userid)))
            logger.debug(response)
            self.send(text_data=json.dumps(response))
        elif request=='save-users':
            message = self._chg_user_bindings(course, parsed.get('ids'), parsed.get('marked_ids', []))
            if message:
                response['feedback'] = message
                response['refresh'] = render_to_string('widgets/table_users.html', {'pk': course_id, 'table': course.table_attendee(User.objects.get(id=self.userid))})
                self.send(text_data=json.dumps(response))
        else:
            logger.critical(request)


class CourseConfigConsumer(SyncSkeleton, Config):
    template='education/course/card_teacher.html'
    instance_reference='course'

    @property
    def template_kwargs(self):
        return {"user": self.scope['user']}

    def get_course(self, course_id):
        c=Course.objects.get(id = course_id)
        assert self.userid in map(lambda o:o.id, c.teachers), "You are not a teacher to config"
        return c


    def receive(self, text_data):
        from hub.models import Profile
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
            if not Profile.objects.filter(user__id=self.get_userid(), can_createcourse=True).first():
                return
            canvas_id=changes.pop('canvasid', None)
            _name=changes.pop('name')
            _folder=f"{datetime.datetime.now().year}-{standardize_str(_name)}" #FIXME settings.py-ba át lehetne tenni, year 
            course=Course.objects.create(name=_name, preferred_image_id=changes.pop('image'), description=changes.pop('description'), folder=_folder)
            binding=UserCourseBinding.objects.create(user_id=self.get_userid(), course=course, is_teacher=True)
            if canvas_id:
                # logger.debug(f"Course has canvasid {canvas_id}.")
                from canvas.models import CanvasCourse, Canvas
                canvas=Canvas.objects.get(user_id=self.get_userid())
                #FIXME: keep canvasname
                canvascourse=CanvasCourse.objects.create(name=course.name, canvas_course_id=canvas_id, course=course, canvas=canvas)
                for cs in canvascourse.get_course_students(canvas.token):
                    UserCourseBinding.objects.create(course=course, user=cs)
                for ct in canvascourse.get_course_teachers(canvas.token):
                    UserCourseBinding.objects.get_or_create(course=course, user=ct, is_teacher=True)
            self._msg(course, f"New course {course.name} is created", reload=True)
        else:
            cid = int(pk)
            course = self.get_course(cid)
        # Iterate over the changes and try to update the model instance
        for field, new_value in changes.items():
            if field == 'image':
                new_value=Image.objects.get(id=new_value)
                self._chg_image(course, new_value, attribute='preferred_image')
            elif field=="volumes":
                self._chg_bindings(course, new_value, Volume, VolumeCourseBinding, 'volume', f"Course mounts of {course.name} changed:\n")
            # Check if the field is a valid attribute of the model
            elif self.is_model_field(course, field):
                old_value = getattr(course, field)
                try:
                    m=f"Attribute {field} of course {course.name} changed from {getattr(course, field)} to {new_value}"
                    # Try assigning the new value to the model's field
                    setattr(course, field, new_value)
                    # Run Django's model validation for the field
                    course.full_clean(validate_unique=True, exclude=[f for f in changes.keys() if f != field])
                    self._msg(course, m)
                    course.save()
                except ValidationError as e:
                    # Validation failed, record the error message
                    failed[field] = { "error": str(e), "value": old_value }
                    self._msg(course, f"Problem configuring course {course.name}", errors=failed)
            else:
                # Attribute does not exist on the model
                logger.error(f"Course model attribute {field} does not exist.")
