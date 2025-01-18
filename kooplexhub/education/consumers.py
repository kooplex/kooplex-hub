import logging
import json
import threading

import pandas
from django_pandas.io import read_frame
from django.template.loader import render_to_string

from channels.generic.websocket import WebsocketConsumer

from education.models import UserAssignmentBinding, Assignment, UserCourseBinding, CourseContainerBinding
from education.forms import TableAssignmentHandle

logger = logging.getLogger(__name__)

#FIXME: code repetition!
from django.db.models.query import QuerySet
class SyncConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_authenticated:
            return
        self.accept()
        self.userid = int(self.scope["url_route"]["kwargs"].get('userid'))
        assert self.scope['user'].id == self.userid, "not authorized"

    def disconnect(self, close_code):
        pass

class AssignmentConsumer(SyncConsumer):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        userid = parsed.get('user_id')
        assignment_id = parsed.get('assignment_id')
        group_id = parsed.get('group_id')
        # authorize
        assignment = Assignment.objects.get(id = assignment_id)
        UserCourseBinding.objects.get(user__id = userid, course = assignment.course, is_teacher = True)
        if group_id == "all":
            students = [ b.user for b in assignment.course.studentbindings ]
        else:
            groups = { 'n' if g is None else str(g.id): students for g, students in assignment.course.groups.items() }
            students = groups[group_id]
        bindings_present = list(UserAssignmentBinding.objects.filter(assignment = assignment, user__in = students))
        students_present = [ b.user for b in bindings_present ]
        bindings = [ UserAssignmentBinding(user = u, assignment = assignment) for u in students if u not in students_present ]
        bindings.extend(bindings_present)
        t = TableAssignmentHandle(bindings)
        self.send(text_data = json.dumps(f"""<h6 class="">Handle assignment {assignment.name}</h6>{t.as_html(None)}"""))


class AssignmentSummaryConsumer(SyncConsumer):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        self.send(text_data = json.dumps(parsed)) #ping
        userid = parsed.get('user_id')
        courseid = parsed.get('course_id')
        # authorize
        course = UserCourseBinding.objects.get(user__id = userid, course__id = courseid, is_teacher = True).course
        bindings = UserAssignmentBinding.objects.filter(assignment__course = course)
        if bindings.count() == 0:
            self.send(text_data = json.dumps(f"""<h6 class="">There are no assignments in this course {course.name}</h6>"""))
            return None
        dfm = read_frame(bindings)
        table = dfm.pivot(index = "user", columns = "assignment", values = "score")
        table.columns = [tc.split("Assignment ")[1].split(" (")[0] for tc in table.columns]
        points = dfm.fillna(0).groupby(by="user").agg("sum")[["score"]].rename(columns={"score":"Total points"})
        result = pandas.merge(left=table, right=points, left_on="user", right_on="user", how="inner")
        t = result.to_html(classes = "table table-bordered table-striped text-center", index_names = False, justify = "center", na_rep = "—", border = None)
        self.send(text_data = json.dumps(f"""<h6 class="">The score table for course {course.name}</h6>{t}"""))

#################

class CourseGetContainersConsumer(SyncConsumer):
    def receive(self, text_data):
        parsed = json.loads(text_data)
        logger.debug(parsed)
        #assert parsed.get('request')=='configure-project', "wrong request"
        courseid = parsed.get('pk')
        bindings = CourseContainerBinding.objects.filter(container__user__id=self.userid, course__id=courseid)
        message_back = {
            "feedback": f"Container list refreshed",
            "response": render_to_string("widgets/widget_containertable.html", {"containers": map(lambda o: o.container, bindings) }),
        }
        logger.debug(message_back)
        self.send(text_data=json.dumps(message_back))

