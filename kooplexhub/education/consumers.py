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

from hub.util import SyncSkeleton, AsyncSkeleton, normalize_pk
from .models import Course, VolumeCourseBinding
from .templatetags.course_buttons import render_attendees
from volume.models import Volume

from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()

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


class AssignmentConfigureHandler:
    @staticmethod
    def create_table_class(df, editable_columns):
        import django_tables2 as tables
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

    def __init__(self, instance, user):
        self.course = instance
        self.user = user
        self.dispatcher = {
            'list-new': self.handle_tab_new,
            'list-config': self.handle_tab_config,
            'list-individual': self.handle_tab_individual,
            'list-summary': self.handle_tab_summary,
            'new-assignment': self.handle_assignment_create,
            'configure-assignment': self.handle_assignment_config,
            'handout-assignment': self.handle_assignment_handout,
            'collect-assignment': self.handle_assignment_collect,
            'reassign-assignment': self.handle_assignment_reassign,
            'delete-assignment': self.handle_assignment_delete,
            'manage-individual': self.handle_individual,
        }

    @property
    def assignments(self):
        return Assignment.objects.filter(course=self.course)

    def handle_query(self, query, data):
        handler = self.dispatcher.get(query)
        if handler:
            return handler(data)
        else:
            logger.critical(f"No handler for assignment configurator: {query}")

    def handle_tab_new(self, data):
        folders=self.course.dir_assignmentcandidate()
        return { '[data-tab=new]': render_to_string('education/assignment/new.html', {
            'course': self.course, 'folders': folders, 
            'table': TableAssignmentConf([Assignment()], exclude_columns=['manage', 'delete'])}) 
        }

    def handle_tab_config(self, data):
        return { '[data-tab=config]': render_to_string('education/assignment/config.html', { 'table': TableAssignmentConf(self.assignments) }) }

    def handle_tab_individual(self, data):
        UAbind_dict = {
            (ua.user_id, ua.assignment_id): ua.state
            for ua in UserAssignmentBinding.objects.filter(assignment__in=self.assignments)
        }
        return { '[data-tab=individual]': render_to_string('education/tables/assignment_individual.html', {
            'assignments': self.assignments, 'students': self.course.students, 'bindings': UAbind_dict})
        }

    def handle_tab_summary(self, data):
        #dfm = read_frame(UserAssignmentBinding.objects.filter(assignment__course = course)).fillna(pandas.NA)
        dfm = read_frame(UserAssignmentBinding.objects.filter(assignment__course = self.course)).fillna(numpy.nan)
        dfm=dfm[['user', 'assignment', 'score']]
        if dfm.empty:
            t_score=None
        else:
            try:
                table = dfm.pivot(index = "user", columns = "assignment", values = "score")
                table.columns = [tc.split("Assignment ")[1].split(" (")[0] for tc in table.columns]  #FIXME: not a very nice way to parse
                points = dfm.fillna(0).groupby(by="user").agg("sum")[["score"]].rename(columns={"score":"Total points"})
                result = pandas.merge(left=table, right=points, left_on="user", right_on="user", how="inner").reset_index()
                EditableTable = self.create_table_class(result, table.columns)
                t_score = EditableTable(result.fillna("—").to_dict(orient='records'))  # Convert DataFrame to Django Table
            except Exception as e:
                logger.critical(f"FIXME pivot -- {e}")
                t_score=None
        return { '[data-tab=summary]': render_to_string('education/tables/assignment_scores.html', {
            'table': t_score, "course_id": self.course.id}) 
        }

    def handle_assignment_create(self, data):
        attributes = { 'course': self.course, 'creator': self.user }
        attributes.update(data['attributes'])
        try:
            Assignment.objects.create(**attributes).snapshot() #FIXME signal
        except Exception as e:
            logger.critical(e)
        return self.handle_tab_new({})

    def handle_assignment_config(self, data):
        for r in data.get('changes'):
            a=Assignment.objects.get(pk=r['id'])
            for attr, new_value in r['changed'].items():
                setattr(a, attr, new_value)
            a.save()
        return self.handle_tab_config({})

    def handle_assignment_handout(self, data):
        for a in self.assignments.filter(id__in=data['handout']):
            a.handout()
        return self.handle_tab_config({})

    def handle_assignment_collect(self, data):
        for a in self.assignments.filter(id__in=data['collect']):
            a.collect()
        return self.handle_tab_config({})

    def handle_assignment_reassign(self, data):
        for a in self.assignments.filter(id__in=data['reassign']):
            a.reassign()
        return self.handle_tab_config({})

    def handle_assignment_delete(self, data):
        Assignment.objects.filter(pk__in=data['remove']).delete()
        return self.handle_tab_config({})

    def handle_individual(self, data):
        from .templatetags.course_tags import render_busy
        for t in data.get('individual'):
            b, _ = UserAssignmentBinding.objects.get_or_create(user_id=t['user_id'], assignment_id=t['assignment_id'])
            if t['todo']=='handout':
                b.handout()
            if t['todo']=='collect':
                b.collect()
            if t['todo']=='reassign':
                b.reassign()
        return { '[data-tab=individual]': render_busy('individual') }


class AssignmentConsumer(SyncSkeleton):
    def receive(self, text_data):
        parsed=json.loads(text_data)
        logger.debug(parsed)
        course_id=parsed.get('pk')
        try:
            b=UserCourseBinding.objects.get(user__id=self.userid, course__id=course_id, is_teacher=True)
        except UserCourseBinding.DoesNotExist:
            logger.error(parsed)
            return
        dispatcher = AssignmentConfigureHandler(b.course, b.user)
        query=parsed.get('query')
        re=dispatcher.handle_query(query, parsed)
        self.send(text_data=json.dumps({
            "feedback": 'Assignment pane refreshed',
            'replace_widgets': re,
        }))



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
            "replace_widgets": {
                f'[id=environmentControl-{courseid}]': render_to_string("container/table_control_shortcut.html", {"containers": list(map(lambda o: o.container, bindings)), "pk": ucb.id, "objectId": courseid }),
            },
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
                response['refresh'] = render_to_string('widgets/table_users.html', render_attendees(course, User.objects.get(id=self.userid)))
                self.send(text_data=json.dumps(response))
        else:
            logger.critical(request)


class CourseConfigHandler:
    def __init__(self, instance, user):
        self.instance = instance
        self.user = user
        self.attribute_handlers = {
            'name': (False, self.handle_name_update),
            'description': (False, self.handle_description_update),
            'preferred_image': (False, self.handle_image_update),
            'volumes': (True, self.handle_mounts_update),
        }

    def handle_attribute(self, attribute_name, new_value):
        pass_attribute, handler = self.attribute_handlers.get(attribute_name)
        if handler and pass_attribute:
            return handler(attribute_name, new_value)
        elif handler:
            return handler(new_value)
        else:
            logger.critical(f"No handler for container configuration attribute: {attribute_name}")

    def handle_name_update(self, new_value):
        from .templatetags.course_tags import render_name
        old_value = self.instance.name
        self.instance.name = new_value
        try:
            self.instance.full_clean()
            self.instance.save()
            return f"name changed from {old_value} to {new_value}", {f"[data-name=name][data-pk={self.instance.pk}][data-model=course]": render_name(self.instance)}
        except ValidationError as e:
            return str(e), {
                f"[data-name=name][data-pk={self.instance.pk}][data-model=course]": render_name(
                    self.instance, 
                    error=e.message_dict.get("name", ["Unknown error"])[0],
                    original_value=old_value
                )}

    def handle_description_update(self, new_value):
        from .templatetags.course_tags import render_description
        old_value = self.instance.description
        self.instance.description = new_value
        try:
            self.instance.full_clean()
            self.instance.save()
            return f"description changed from {old_value} to {new_value}", {f"[data-name=description][data-pk={self.instance.pk}][data-model=course]": render_description(self.instance)}
        except ValidationError as e:
            return str(e), {
                f"[data-name=description][data-pk={self.instance.pk}][data-model=course]": render_description(
                    self.instance,
                    error=e.message_dict.get("description", ["Unknown error"])[0],
                    original_value=old_value
                )}

    def handle_image_update(self, new_value):
        from container.templatetags.container_buttons import button_image
        from container.models import Image
        old_value = self.instance.preferred_image.name
        image = Image.objects.get(id=new_value)
        self.instance.preferred_image = image
        self.instance.save()
        return f"image changed from {old_value} to {image.name}", {f"[data-name=preferred_image][data-pk={self.instance.pk}][data-model=course]": button_image(self.instance, 'course', 'preferred_image')}

    def handle_mounts_update(self, attribute, new_value):
        from .templatetags.course_tags import render_volumes
        obj_type, bind_type = Volume, VolumeCourseBinding
        attribute='volume'
        a=[]
        r=[]
        m=f"mounts changed: "
        n = lambda b: getattr(b, attribute).folder
        for o in obj_type.objects.filter(id__in = new_value):
            b, _=bind_type.objects.get_or_create(**{attribute: o, 'course': self.instance})
            a.append(n(b))
        for b in bind_type.objects.filter(course=self.instance).exclude(**{f"{attribute}__id__in": new_value}):
            r.append(n(b))
            b.delete()
        if a:
            m += "added " + ", ".join(a) + "\n"
        if r:
            m += "removed " + ", ".join(r) + "\n"
        if a or r:
            return m, {f"[data-name=volumes][data-pk={self.instance.pk}][data-model=course]": render_volumes(self.instance, self.user)}
        else:
            return "", {}


class CourseConfigConsumer(SyncSkeleton):
    @property
    def template_kwargs(self):
        return {"user": self.scope['user']}

    def get_course(self, course_id):
        c=Course.objects.get(id = course_id)
        assert self.userid in map(lambda o:o.id, c.teachers), "You are not a teacher to config"
        return c


    def receive(self, text_data):
        from container.templatetags.container_buttons import button_image
        from hub.models import Profile
        from container.models import Image
        from kooplexhub.lib.libbase import standardize_str
        import datetime
        parsed = json.loads(text_data)
        logger.debug(parsed)
        request = parsed.get('request')
        user = User.objects.get(pk=self.userid)
        if request == "create-course":
            if not Profile.objects.filter(user__id=self.get_userid(), can_createcourse=True).first():
                return
            canvas_id=parsed.pop('canvasid', None)
            _name=parsed.get('name')
            _folder=f"{datetime.datetime.now().year}-{standardize_str(_name)}" #FIXME settings.py-ba át lehetne tenni, year 
            course=Course.objects.create(name=_name, preferred_image_id=parsed.get('preferred_image'), description=parsed.get('description'), folder=_folder)
            binding=UserCourseBinding.objects.create(user_id=self.get_userid(), course=course, is_teacher=True)
            if canvas_id:
                from canvas.models import CanvasCourse
                CanvasCourse.create(binding.user.id, canvas_id, course)
            self.send(text_data=json.dumps({
                'feedback': f"New course {course.name} is created",
                'reload_page': True,
            }))
            configurator = CourseConfigHandler(course, user)
            changes = { k: parsed[k] for k in configurator.attribute_handlers.keys() if k in parsed and not k in ["name", "description", "preferred_image"] }
        elif request =='configure-course':
            pk = parsed.get('pk')
            changes = parsed.get('changes')
            cid = int(pk)
            course = self.get_course(cid)
            configurator = CourseConfigHandler(course, user)
        elif request =='update-widget':
            field=parsed.get('field')
            if field=='name':
                from .templatetags.course_tags import render_name
                mfield = Course._meta.get_field('name')
                try:
                    value=parsed.get('value')
                    mfield.clean(value, model_instance=None)
                    self.send(text_data=json.dumps({'replace_widgets': {
                        f"[data-name=name][data-pk=None][data-model=course]": render_name(value=parsed.get('value'),
                        )}
                    }))
                except ValidationError as e:
                    #FIXME check uniqueness!
                    self.send(text_data=json.dumps({'replace_widgets': {
                        f"[data-name=name][data-pk=None][data-model=course]": render_name(value=parsed.get('value'),
                            error=', '.join(e.messages),
                        )}
                    }))
            elif field=='description':
                from .templatetags.course_tags import render_description
                mfield = Course._meta.get_field('description')
                try:
                    value=parsed.get('value')
                    mfield.clean(value, model_instance=None)
                    self.send(text_data=json.dumps({'replace_widgets': {
                        f"[data-name=description][data-pk=None][data-model=course]": render_description(value=parsed.get('value'),
                        )}
                    }))
                except ValidationError as e:
                    self.send(text_data=json.dumps({'replace_widgets': {
                        f"[data-name=description][data-pk=None][data-model=course]": render_description(value=parsed.get('value'),
                            error=', '.join(e.messages),
                        )}
                    }))
            elif field=='preferred_image':
                image = Image.objects.get(id=parsed.get('value'))
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=preferred_image][data-pk=None][data-model=course]": button_image(model='course', attr='preferred_image', value=image)}}))
            elif field=='volumes':
                from .templatetags.course_tags import render_volumes
                from volume.models import Volume
                self.send(text_data=json.dumps({'replace_widgets': {f"[data-name=volumes][data-pk=None][data-model=course]": render_volumes(None, user, value=Volume.objects.filter(pk__in=parsed.get('value'))) }}))
            else:
                logger.critical(f"unknown {field}")
            return
        else:
            logger.error(f"wrong request: {request}")
            return
        failed={}
        # Iterate over the changes and try to update the model instance
        widgets={}
        messages=[]
        for field, new_value in changes.items():
            m, w = configurator.handle_attribute(field, new_value)
            messages.append(m)
            widgets.update(w)
        if messages:
            self.send(text_data=json.dumps({
                'feedback': f"Course {course.name} is configured: " + ",".join(messages) + ".",
                'replace_widgets': widgets,
            }))

